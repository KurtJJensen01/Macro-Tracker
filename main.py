from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
DB_NAME = "tracker.db"


# Create DB on first run
def init_db():
    if not os.path.exists(DB_NAME):
        with sqlite3.connect(DB_NAME) as conn:
            with open("schema.sql", "r") as f:
                conn.executescript(f.read())


@app.before_request
def before_request():
    init_db()


@app.route("/")
def index():
    return redirect(url_for("food_log"))


@app.route("/food", methods=["GET", "POST"])
def food_log():
    today = datetime.now().strftime("%Y-%m-%d")

    # Handle new food submission
    if request.method == "POST":
        name = request.form["name"].strip()
        calories = float(request.form["calories"])
        protein = float(request.form.get("protein", 0))
        carbs = float(request.form.get("carbs", 0))
        fat = float(request.form.get("fat", 0))

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()

            # Add to saved_foods if it's not already there
            cur.execute("INSERT OR IGNORE INTO saved_foods (name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?)",
                        (name, calories, protein, carbs, fat))

            # Add to food_logs
            cur.execute("INSERT INTO food_logs (name, calories, protein, carbs, fat, date) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, calories, protein, carbs, fat, today))
            conn.commit()

        return redirect(url_for("food_log"))

    # Fetch today's food logs
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, calories, protein, carbs, fat FROM food_logs WHERE date = ?", (today,))
        food_entries = cur.fetchall()

    # Calculate totals
    totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for entry in food_entries:
        totals["calories"] += entry[2]
        totals["protein"] += entry[3]
        totals["carbs"] += entry[4]
        totals["fat"] += entry[5]

    return render_template("food.html", title="Food Log", entries=food_entries, totals=totals)


@app.route("/weight", methods=["GET", "POST"])
def weight_log():
    if request.method == "POST":
        date = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")
        time_of_day = request.form.get("time_of_day")
        weight = request.form.get("weight")
        if time_of_day not in ("morning", "night") or not weight:
            return "Invalid input", 400
        weight = float(weight)

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO weight_logs (date, time_of_day, weight) VALUES (?, ?, ?)",
                (date, time_of_day, weight),
            )
            conn.commit()
        return redirect(url_for("weight_log"))

    # Fetch morning and night weights separately for display
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, date, weight FROM weight_logs WHERE time_of_day = 'morning' ORDER BY date"
        )
        morning_weights = cur.fetchall()

        cur.execute(
            "SELECT id, date, weight FROM weight_logs WHERE time_of_day = 'night' ORDER BY date"
        )
        night_weights = cur.fetchall()

    return render_template(
        "weight.html",
        title="Weight Log",
        morning_weights=morning_weights,
        night_weights=night_weights,
    )


@app.route("/weight/delete/<int:id>", methods=["POST"])
def delete_weight(id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM weight_logs WHERE id = ?", (id,))
        conn.commit()
    return redirect(url_for("weight_log"))



@app.route("/settings", methods=["GET", "POST"])
def settings():
    macros = {}
    latest_weight = get_latest_weight()
    tdee = goal = None

    if request.method == "POST":
        tdee = int(request.form["tdee"])
        goal = request.form["goal"]
        now = datetime.now()

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM tdee_settings")
            cur.execute("INSERT INTO tdee_settings (tdee, goal, last_updated) VALUES (?, ?, ?)", (tdee, goal, now))
            conn.commit()

    # Load saved settings
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT tdee, goal FROM tdee_settings ORDER BY last_updated DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            tdee, goal = row

    
    # Always include latest weight if it exists
    if latest_weight:
        macros["weight"] = latest_weight

    # Then calculate macros if we also have tdee and goal
    if tdee and goal and latest_weight:
        protein = round(latest_weight * PROTEIN_MULTIPLIERS[goal])
        fat = round(latest_weight * FAT_MULTIPLIERS[goal])
        carbs = round((int(tdee) - (protein * 4 + fat * 9)) / 4)
        macros.update({
            "protein": protein,
            "fat": fat,
            "carbs": carbs,
            "tdee": tdee,
            "goal": goal
        })


    return render_template("settings.html", title="Settings", macros=macros)


# Macro multipliers based on goal
PROTEIN_MULTIPLIERS = {
    "Mild Cut": 1.15,
    "Moderate Cut": 1.25,
    "Aggressive Cut": 1.4,
    "Maintenance": 1.05,
    "Lean Bulk": 0.95,
    "Aggressive Bulk": 0.85
}

FAT_MULTIPLIERS = {
    "Mild Cut": 0.4,
    "Moderate Cut": 0.35,
    "Aggressive Cut": 0.3,
    "Maintenance": 0.45,
    "Lean Bulk": 0.45,
    "Aggressive Bulk": 0.35
}


def get_latest_weight():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT weight FROM weight_logs
            ORDER BY date DESC, 
                     CASE time_of_day 
                         WHEN 'morning' THEN 1 
                         WHEN 'night' THEN 0 
                         ELSE 2 
                     END
            LIMIT 1
        """)
        row = cur.fetchone()
        return row[0] if row else None



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)

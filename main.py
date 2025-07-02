from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import sqlite3
import os
from datetime import datetime
import csv
from io import StringIO

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


    from datetime import datetime


@app.route("/food", methods=["GET", "POST"])
def food_log():
    selected_date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

    if request.method == "POST":
        name = request.form["name"].strip()
        try:
            calories = float(request.form["calories"])
            protein = float(request.form.get("protein", 0))
            carbs = float(request.form.get("carbs", 0))
            fat = float(request.form.get("fat", 0))
        except ValueError:
            flash("Please enter valid numbers for calories and macros.", "error")
            return redirect(url_for("food_log", date=selected_date))

        if not name:
            flash("Food name is required.", "error")
            return redirect(url_for("food_log", date=selected_date))
        if calories <= 0:
            flash("Calories must be a positive number.", "error")
            return redirect(url_for("food_log", date=selected_date))
        if protein < 0 or carbs < 0 or fat < 0:
            flash("Macros cannot be negative.", "error")
            return redirect(url_for("food_log", date=selected_date))

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO saved_foods (name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?)",
                        (name, calories, protein, carbs, fat))
            cur.execute("INSERT INTO food_logs (name, calories, protein, carbs, fat, date) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, calories, protein, carbs, fat, selected_date))
            conn.commit()

        return redirect(url_for("food_log", date=selected_date))

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, calories, protein, carbs, fat FROM food_logs WHERE date = ?", (selected_date,))
        food_entries = cur.fetchall()
        cur.execute("SELECT * FROM saved_foods ORDER BY name")
        saved_foods = cur.fetchall()


    totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for entry in food_entries:
        totals["calories"] += entry[2]
        totals["protein"] += entry[3]
        totals["carbs"] += entry[4]
        totals["fat"] += entry[5]

    now_date = datetime.now().strftime("%Y-%m-%d")

    # Get macro targets from TDEE settings or use defaults
    macro_targets = get_macro_targets()

    return render_template(
        "food.html",
        title="Food Log",
        entries=food_entries,
        totals=totals,
        saved_foods=saved_foods,
        selected_date=selected_date,
        now_date=now_date,
        macro_targets=macro_targets,
    )


@app.route("/food/delete/<int:food_id>", methods=["POST"])
def delete_food(food_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM food_logs WHERE id = ?", (food_id,))
        conn.commit()
    return redirect(url_for("food_log"))


@app.route("/food/edit/<int:food_id>", methods=["GET", "POST"])
def edit_food(food_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        if request.method == "POST":
            name = request.form["name"]
            calories = float(request.form["calories"])
            protein = float(request.form["protein"])
            carbs = float(request.form["carbs"])
            fat = float(request.form["fat"])
            cur.execute("""
                UPDATE food_logs 
                SET name = ?, calories = ?, protein = ?, carbs = ?, fat = ? 
                WHERE id = ?
            """, (name, calories, protein, carbs, fat, food_id))
            conn.commit()
            return redirect(url_for("food_log"))
        else:
            cur.execute("SELECT name, calories, protein, carbs, fat FROM food_logs WHERE id = ?", (food_id,))
            food = cur.fetchone()
            return render_template("edit_food.html", food_id=food_id, food=food)


@app.route("/api/saved-food/<path:name>")
def get_saved_food(name):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, calories, protein, carbs, fat FROM saved_foods WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return {
                "name": row[0],
                "calories": row[1],
                "protein": row[2],
                "carbs": row[3],
                "fat": row[4]
            }
        else:
            return {"error": "Food not found"}, 404


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

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Night weights & calories same date
        cur.execute(
            """
            SELECT w.id, w.date, w.weight,
                IFNULL(f.total_calories, 0) AS calories
            FROM weight_logs w
            LEFT JOIN (
                SELECT date, SUM(calories) AS total_calories
                FROM food_logs
                GROUP BY date
            ) f ON f.date = w.date
            WHERE w.time_of_day = 'night'
            ORDER BY w.date
            """
        )
        night_weights = cur.fetchall()

        # Morning weights & calories previous day
        cur.execute(
            """
            SELECT w.id, w.date, w.weight,
                IFNULL(f.total_calories, 0) AS calories
            FROM weight_logs w
            LEFT JOIN (
                SELECT date, SUM(calories) AS total_calories
                FROM food_logs
                GROUP BY date
            ) f ON f.date = DATE(w.date, '-1 day')
            WHERE w.time_of_day = 'morning'
            ORDER BY w.date
            """
        )
        morning_weights = cur.fetchall()

    # Convert to dicts
    morning_weights_list = [dict(row) for row in morning_weights]
    night_weights_list = [dict(row) for row in night_weights]

    # Create calories lookup by date
    morning_calories = {row['date']: row['calories'] for row in morning_weights_list}
    night_calories = {row['date']: row['calories'] for row in night_weights_list}

    return render_template(
        "weight.html",
        title="Weight Log",
        morning_weights=morning_weights_list,
        night_weights=night_weights_list,
        morning_calories=morning_calories,
        night_calories=night_calories,
        datetime=datetime
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


@app.route('/export/food_logs')
def export_food_logs():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT date, name, calories, protein, carbs, fat FROM food_logs ORDER BY date DESC")
        data = cur.fetchall()

    headers = ["Date", "Name", "Calories", "Protein", "Carbs", "Fat"]
    csv_generator = generate_csv(data, headers)
    return Response(
        csv_generator(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment;filename=saved_foods.csv"}
    )



@app.route('/export/weight_logs')
def export_weight_logs():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT date, time_of_day, weight FROM weight_logs ORDER BY date DESC")
        data = cur.fetchall()

    headers = ["Date", "Time of Day", "Weight"]
    csv_generator = generate_csv(data, headers)
    return Response(
        csv_generator(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment;filename=saved_foods.csv"}
    )



@app.route('/export/saved_foods')
def export_saved_foods():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, calories, protein, carbs, fat FROM saved_foods ORDER BY name")
        data = cur.fetchall()

    headers = ["Name", "Calories", "Protein", "Carbs", "Fat"]
    csv_generator = generate_csv(data, headers)
    return Response(
        csv_generator(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment;filename=saved_foods.csv"}
    )



@app.route("/api/saved-food-search")
def saved_food_search():
    query = request.args.get("q", "").strip().lower()

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        if query:
            results = conn.execute(
                "SELECT name FROM saved_foods WHERE LOWER(name) LIKE ? ORDER BY name",
                ('%' + query + '%',)
            ).fetchall()
        else:
            # No limit when query is empty
            results = conn.execute(
                "SELECT name FROM saved_foods ORDER BY name"
            ).fetchall()

        return jsonify([{"name": row["name"]} for row in results])


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


def get_macro_targets():
    """Get macro targets from TDEE settings or return defaults"""
    latest_weight = get_latest_weight()
    
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT tdee, goal FROM tdee_settings ORDER BY last_updated DESC LIMIT 1")
        row = cur.fetchone()
    
    # If we have all the data, calculate macros
    if row and latest_weight:
        tdee, goal = row
        protein = round(latest_weight * PROTEIN_MULTIPLIERS[goal])
        fat = round(latest_weight * FAT_MULTIPLIERS[goal])
        carbs = round((int(tdee) - (protein * 4 + fat * 9)) / 4)
        
        return {
            "calories": int(tdee) + FITNESS_GOAL[goal],
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
        }
    
    # Fallback to defaults if no settings or weight
    return {
        "calories": 2500,
        "protein": 180,
        "carbs": 300,
        "fat": 70,
    }


def generate_csv(data, headers):
    def generate():
        # Yield UTF-8 BOM first (helps Excel detect UTF-8)
        yield '\ufeff'

        output = StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow(headers)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in data:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
    return generate



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

FITNESS_GOAL = {
    "Mild Cut": -350,
    "Moderate Cut": -550,
    "Aggressive Cut": -850,
    "Maintenance": 0,
    "Lean Bulk": 250,
    "Aggressive Bulk": 550
}

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)

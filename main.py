from flask import Flask, render_template, request, redirect, url_for
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


@app.route("/food")
def food_log():
    return render_template("base.html", title="Food Log")


@app.route("/weight")
def weight_log():
    return render_template("base.html", title="Weight Log")


@app.route("/settings")
def settings():
    return render_template("base.html", title="Settings")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)

from flask import jsonify

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
            WHERE date = (SELECT MAX(date) FROM weight_logs)
            ORDER BY time_of_day = 'morning' DESC, time_of_day = 'night' DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        return row[0] if row else None

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

    # Calculate macros if possible
    if tdee and goal and latest_weight:
        protein = round(latest_weight * PROTEIN_MULTIPLIERS[goal])
        fat = round(latest_weight * FAT_MULTIPLIERS[goal])
        carbs = round((int(tdee) - (protein * 4 + fat * 9)) / 4)
        macros = {
            "protein": protein,
            "fat": fat,
            "carbs": carbs,
            "tdee": tdee,
            "goal": goal,
            "weight": latest_weight
        }

    return render_template("settings.html", title="Settings", macros=macros)

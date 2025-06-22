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

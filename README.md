# Macro Tracker

A mobile-friendly macro and weight tracking app built with Flask.

## About

This app was custom-designed to help track my calorie and macro intake in a way that supports my **fast metabolism** and **ulcerative colitis (UC)**. I needed a lightweight, personalized tool that could:

- Track both **morning** and **night** weight entries.
- Log and store **daily food intake** with macros (calories, protein, carbs, fat).
- **Display calories consumed next to weight logs** to help identify trends.
- Visualize **weight over time** with a line graph, including hoverable calorie tooltips.
- Be **optimized for mobile use** (e.g., Safari on iPhone).

## Features

- 📆 Log food and weight daily
- 🍗 Input macros (calories, protein, carbs, fat)
- 📈 See weight and calories on interactive graphs
- 🌓 Toggle between morning and night logs
- 📤 Export data to CSV (planned)
- 🌙 Dark mode support
- 📱 Designed for mobile-first usage

## Tech Stack

- **Python** & **Flask** (backend)
- **SQLite** (database)
- **HTML/CSS** + **Jinja2** (frontend)
- **Chart.js** (graphing)
- **JavaScript** (UX enhancements)

## How to Run Locally

```bash
git clone https://github.com/yourusername/macro-tracker.git
cd macro-tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

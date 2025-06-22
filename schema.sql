-- Create TDEE and goal settings
CREATE TABLE IF NOT EXISTS tdee_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tdee INTEGER,
    goal TEXT,
    last_updated TIMESTAMP
);

-- Weight logs
CREATE TABLE IF NOT EXISTS weight_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    time_of_day TEXT CHECK(time_of_day IN ('morning', 'night')),
    weight REAL
);

-- Saved food items
CREATE TABLE IF NOT EXISTS saved_foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    calories INTEGER,
    protein REAL,
    carbs REAL,
    fat REAL
);

-- Food logs
CREATE TABLE IF NOT EXISTS food_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    food_id INTEGER,
    custom_name TEXT,
    calories INTEGER,
    protein REAL,
    carbs REAL,
    fat REAL,
    timestamp TEXT,
    FOREIGN KEY (food_id) REFERENCES saved_foods(id)
);

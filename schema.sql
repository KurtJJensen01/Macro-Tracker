-- TDEE and goal settings
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

-- Saved foods (for reuse/autofill)
CREATE TABLE IF NOT EXISTS saved_foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    calories REAL NOT NULL,
    protein REAL,
    carbs REAL,
    fat REAL
);

-- Food logs
CREATE TABLE IF NOT EXISTS food_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    calories REAL NOT NULL,
    protein REAL,
    carbs REAL,
    fat REAL,
    date TEXT NOT NULL,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

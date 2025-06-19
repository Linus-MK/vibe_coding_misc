-- Drop the table if it exists to start fresh during development
DROP TABLE IF EXISTS tasks;

-- Create the tasks table
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    prep_time_seconds INTEGER NOT NULL DEFAULT 15,
    duration_minutes INTEGER NOT NULL,
    url TEXT
); 
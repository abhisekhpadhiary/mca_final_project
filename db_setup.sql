-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    college_name TEXT,
    profile_pic TEXT DEFAULT 'default_avatar.png',

    -- ✅ NEW COLUMN (IMPORTANT)
    status TEXT DEFAULT 'active'
);

------------------------------------------------------

-- EXAMS TABLE
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_name TEXT,
    subject TEXT,
    description TEXT,
    start_time TEXT,
    duration INTEGER,
    examiner_id INTEGER,
    random_password TEXT,
    results_published INTEGER DEFAULT 0
);

------------------------------------------------------

-- QUESTIONS TABLE
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER,
    question_text TEXT,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_answer TEXT
);

------------------------------------------------------

-- RESULTS TABLE
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    exam_id INTEGER,
    score INTEGER,
    total_questions INTEGER,
    percentage REAL,
    status TEXT,
    submitted_at TEXT
);

------------------------------------------------------

-- DELETED EXAMS TABLE (if you use it)
CREATE TABLE IF NOT EXISTS deleted_exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_name TEXT,
    subject TEXT,
    start_time TEXT
);
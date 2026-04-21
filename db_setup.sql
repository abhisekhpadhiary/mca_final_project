-- =========================
-- USERS TABLE
-- =========================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,                  -- student / admin / examiner / developer
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    college_name TEXT NOT NULL,
    profile_pic TEXT DEFAULT 'default_avatar.png',
    status TEXT DEFAULT 'active'         -- pending / active / rejected
);

-- =========================
-- EXAMS TABLE
-- =========================
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT,
    start_time TEXT NOT NULL,
    duration INTEGER NOT NULL,
    random_password TEXT NOT NULL,
    examiner_id INTEGER NOT NULL,
    results_published INTEGER DEFAULT 0,

    -- ✅ CSV FEATURE
    allowed_emails TEXT,

    FOREIGN KEY (examiner_id) REFERENCES users(id)
);

-- =========================
-- DELETED EXAMS TABLE
-- =========================
CREATE TABLE IF NOT EXISTS deleted_exams (
    id INTEGER PRIMARY KEY,
    exam_name TEXT,
    subject TEXT,
    description TEXT,
    start_time TEXT,
    duration INTEGER,
    random_password TEXT,
    examiner_id INTEGER,
    results_published INTEGER,
    allowed_emails TEXT,
    deleted_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- RESULTS TABLE
-- =========================
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    exam_id INTEGER NOT NULL,
    score INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    submitted_at TEXT,

    -- Prevent duplicate attempts
    UNIQUE(user_id, exam_id),

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (exam_id) REFERENCES exams(id)
);
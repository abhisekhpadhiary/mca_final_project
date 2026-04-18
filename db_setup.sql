-- ─── USERS TABLE ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    profile_pic TEXT DEFAULT 'default_avatar.png',
    college_name TEXT 
);

-- ─── EXAMS TABLE ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_name TEXT UNIQUE NOT NULL,
    subject TEXT,
    description TEXT,
    start_time TEXT NOT NULL,
    duration INTEGER NOT NULL,
    random_password TEXT NOT NULL,
    examiner_id INTEGER NOT NULL,
    is_deleted INTEGER DEFAULT 0, 
    -- NEW: Track if results are visible to students
    results_published INTEGER DEFAULT 0,
    FOREIGN KEY (examiner_id) REFERENCES users (id)
);

-- ─── RESULTS TABLE ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    exam_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users (id),
    FOREIGN KEY (exam_id) REFERENCES exams (id),
    UNIQUE(student_id, exam_id)
);
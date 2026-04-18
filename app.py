import os
import random
import string
import base64
import sqlite3
import shutil
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'proctor_secret_key_mca_2026'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'exam_system.db')
EXAM_FILES_DIR = os.path.join(BASE_DIR, 'exam_files')
PROFILE_PICS_DIR = os.path.join(BASE_DIR, 'static/profile_pics')
os.makedirs(PROFILE_PICS_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── DB HELPERS ───────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if os.path.exists(os.path.join(BASE_DIR, 'db_setup.sql')):
        with open(os.path.join(BASE_DIR, 'db_setup.sql'), 'r') as f:
            sql = f.read()
        conn = get_db()
        conn.executescript(sql)
        conn.commit()
        conn.close()

def gen_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def safe_parse_dt(s):
    if not s: return None
    try: return datetime.fromisoformat(s)
    except ValueError:
        for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'):
            try: return datetime.strptime(s, fmt)
            except ValueError: pass
    return None

# ─── AUTH DECORATORS ──────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Access Denied: Master Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def examiner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'examiner':
            flash('Access denied.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'student':
            flash('Access denied.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ─── AUTH ROUTES ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'user_id' in session else redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role') 
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        college_name = request.form.get('college_name', '').strip()
        
        if role == 'examiner':
            flash('Examiners must be registered by a Master Admin.', 'error')
            return render_template('register.html')

        if not all([role, username, email, password, college_name]):
            flash('All fields are required.', 'error')
            return render_template('register.html')
            
        conn = get_db()
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            conn.close()
            flash('This email is already registered.', 'error')
            return render_template('register.html')

        hashed = generate_password_hash(password)
        try:
            conn.execute('''INSERT INTO users (role, username, email, password, college_name) 
                            VALUES (?,?,?,?,?)''', (role, username, email, hashed, college_name))
            conn.commit()
            conn.close()
            flash(f'{role.capitalize()} registration successful!', 'success')
            return redirect(url_for('login'))
        except sqlite3.OperationalError:
            conn.close()
            flash('Database busy, please try again.', 'error')
            return render_template('register.html')
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session.update({
                'user_id': user['id'], 
                'username': user['username'], 
                'email': user['email'], 
                'role': user['role'],
                'profile_pic': user['profile_pic'] or 'default_avatar.png',
                'college': user['college_name']
            })
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if session['role'] == 'admin': return redirect(url_for('admin_dashboard'))
    if session['role'] == 'examiner': return redirect(url_for('examiner_dashboard'))
    return redirect(url_for('student_dashboard'))

# ─── MASTER ADMIN ROUTES ─────────────────────────────────────

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    conn = get_db()
    teachers = conn.execute('''SELECT id, username, email, college_name,
                               (SELECT COUNT(*) FROM exams WHERE examiner_id = users.id AND is_deleted = 0) as exam_count
                               FROM users WHERE role = 'examiner' AND college_name = ?''', (session['college'],)).fetchall()

    global_stats = conn.execute('''SELECT e.id, e.exam_name, u.username as teacher,
                                   (SELECT COUNT(*) FROM results WHERE exam_id = e.id) as student_count,
                                   (SELECT COUNT(*) FROM results WHERE exam_id = e.id AND (CAST(score AS FLOAT)/NULLIF(total_questions, 0)) >= 0.5) as pass_count
                                   FROM exams e JOIN users u ON e.examiner_id = u.id
                                   WHERE e.is_deleted = 0 AND u.college_name = ?''', (session['college'],)).fetchall()
    conn.close()
    return render_template('admin_dashboard.html', teachers=teachers, stats=global_stats)

@app.route('/admin/examiner/<int:teacher_id>/details')
@login_required
@admin_required
def teacher_details(teacher_id):
    conn = get_db()
    teacher = conn.execute('SELECT * FROM users WHERE id = ? AND role = "examiner" AND college_name = ?', 
                           (teacher_id, session['college'])).fetchone()
    if not teacher:
        conn.close()
        flash("Examiner not found.", "error")
        return redirect(url_for('admin_dashboard'))

    exams = conn.execute('SELECT * FROM exams WHERE examiner_id = ? AND is_deleted = 0', (teacher_id,)).fetchall()
    conn.close()
    return render_template('admin_teacher_view.html', teacher=teacher, exams=exams)

@app.route('/admin/create_examiner', methods=['POST'])
@login_required
@admin_required
def create_examiner():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    admin_college = session.get('college') 
    
    if not all([username, email, password]) or not admin_college:
        flash('Data missing.', 'error')
        return redirect(url_for('admin_dashboard'))
        
    hashed = generate_password_hash(password)
    try:
        conn = get_db()
        conn.execute('''INSERT INTO users (role, username, email, password, college_name) 
                        VALUES (?, ?, ?, ?, ?)''', ('examiner', username, email, hashed, admin_college))
        conn.commit()
        conn.close()
        flash(f'Examiner {username} created.', 'success')
    except sqlite3.IntegrityError:
        flash('Email exists.', 'error')
    return redirect(url_for('admin_dashboard'))

# ─── EXAMINER ROUTES ─────────────────────────────────────────

@app.route('/examiner')
@login_required
@examiner_required
def examiner_dashboard():
    conn = get_db()
    active_exams = conn.execute('SELECT * FROM exams WHERE examiner_id = ? AND is_deleted = 0 ORDER BY start_time DESC', (session['user_id'],)).fetchall()
    deleted_count = conn.execute('SELECT COUNT(*) FROM exams WHERE examiner_id = ? AND is_deleted = 1', (session['user_id'],)).fetchone()[0]
    conn.close()
    
    now = datetime.now()
    live_exams, upcoming_exams, completed_exams = [], [], []

    for e in active_exams:
        start = safe_parse_dt(e['start_time'])
        if not start: continue
        end = start + timedelta(minutes=e['duration'])
        if start <= now <= end: live_exams.append(e)
        elif now < start: upcoming_exams.append(e)
        else: completed_exams.append(e)

    return render_template('examiner_dashboard.html', 
                           live_exams=live_exams, upcoming_exams=upcoming_exams, completed_exams=completed_exams,
                           completed_count=len(completed_exams), deleted_count=deleted_count)

@app.route('/examiner/results')
@login_required
@examiner_required
def examiner_results():
    conn = get_db()
    exams = conn.execute('SELECT * FROM exams WHERE examiner_id = ? AND is_deleted = 0 ORDER BY start_time DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('examiner_results.html', exams=exams)

@app.route('/examiner/results/<int:exam_id>')
@login_required
def exam_detail_results(exam_id):
    conn = get_db()
    # Updated: Fetches 'results_published' so the template knows the status
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    
    raw_results = conn.execute('''SELECT u.username, u.email, r.score, r.total_questions, r.submitted_at 
                                  FROM results r JOIN users u ON r.student_id = u.id 
                                  WHERE r.exam_id = ? ORDER BY r.score DESC''', (exam_id,)).fetchall()
    conn.close()

    processed = []
    for r in raw_results:
        res = dict(r)
        tq = res['total_questions']
        
        if tq and tq > 0:
            res['percentage'] = round((res['score'] / tq * 100), 1)
        else:
            res['percentage'] = 0
            
        res['status'] = 'submitted' if res['submitted_at'] else 'in_progress'
        processed.append(res)

    return render_template('exam_detail_results.html', exam=exam, results=processed)

@app.route('/examiner/publish_result/<int:exam_id>', methods=['POST'])
@login_required
@examiner_required
def publish_result(exam_id):
    conn = get_db()
    # Sets the flag to 1 so students can see it
    conn.execute('UPDATE exams SET results_published = 1 WHERE id = ? AND examiner_id = ?', 
                 (exam_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Results have been published! Students can now view their grades.', 'success')
    return redirect(url_for('exam_detail_results', exam_id=exam_id))

@app.route('/examiner/exam/<int:exam_id>/questions')
@login_required
def view_exam_questions(exam_id):
    conn = get_db()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    conn.close()
    if not exam: return redirect(url_for('dashboard'))
    questions, answers = parse_questions(exam['exam_name'])
    return render_template('view_questions.html', exam=exam, questions=questions, answers=answers)

@app.route('/examiner/schedule', methods=['GET', 'POST'])
@login_required
@examiner_required
def schedule_exam():
    if request.method == 'POST':
        exam_name = request.form.get('exam_name', '').strip().replace(' ', '_')
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        start_time = request.form.get('start_time', '').strip()
        duration = request.form.get('duration', '').strip()
        q_file = request.files.get('question_file')
        a_file = request.files.get('answer_file')
        
        if not all([exam_name, subject, start_time, duration, q_file, a_file]):
            flash('All fields required.', 'error')
            return render_template('schedule_exam.html')
            
        password = gen_password()
        folder = os.path.join(EXAM_FILES_DIR, exam_name)
        os.makedirs(folder, exist_ok=True)
        q_file.save(os.path.join(folder, 'question.txt'))
        a_file.save(os.path.join(folder, 'answer.txt'))
        
        conn = get_db()
        conn.execute('''INSERT INTO exams (exam_name, subject, description, start_time, duration, random_password, examiner_id) 
                        VALUES (?,?,?,?,?,?,?)''', (exam_name, subject, description, start_time, int(duration), password, session['user_id']))
        conn.commit()
        conn.close()
        flash('Exam scheduled!', 'success')
        return redirect(url_for('examiner_dashboard'))
    return render_template('schedule_exam.html')

@app.route('/examiner/delete/<int:exam_id>', methods=['POST'])
@login_required
@examiner_required
def delete_exam(exam_id):
    conn = get_db()
    conn.execute('UPDATE exams SET is_deleted = 1 WHERE id = ? AND examiner_id = ?', (exam_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('examiner_dashboard'))

@app.route('/examiner/deleted-records')
@login_required
@examiner_required
def view_deleted_exams():
    conn = get_db()
    deleted = conn.execute('SELECT * FROM exams WHERE examiner_id = ? AND is_deleted = 1 ORDER BY start_time DESC', 
                           (session['user_id'],)).fetchall()
    conn.close()
    return render_template('deleted_exams.html', exams=deleted)

@app.route('/examiner/restore/<int:exam_id>', methods=['POST'])
@login_required
@examiner_required
def restore_exam(exam_id):
    conn = get_db()
    conn.execute('UPDATE exams SET is_deleted = 0 WHERE id = ? AND examiner_id = ?', (exam_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Exam restored!', 'success')
    return redirect(url_for('view_deleted_exams'))

# ─── STUDENT ROUTES ───────────────────────────────────────────

@app.route('/student')
@login_required
@student_required
def student_dashboard():
    conn = get_db()
    now = datetime.now()
    now_str = now.strftime('%Y-%m-%dT%H:%M')
    
    raw_exams = conn.execute('''SELECT e.* FROM exams e JOIN users u ON e.examiner_id = u.id 
                               WHERE e.is_deleted = 0 AND u.college_name = ?
                               ORDER BY e.start_time ASC''', (session.get('college'),)).fetchall()
    conn.close()
    
    upcoming = []
    for e in raw_exams:
        start = safe_parse_dt(e['start_time'])
        if not start:
            continue
        end = start + timedelta(minutes=e['duration'])
        if now > end:
            continue
        exam_dict = dict(e)
        exam_dict['is_live'] = start <= now <= end
        upcoming.append(exam_dict)
    
    return render_template('student_dashboard.html', upcoming=upcoming)

@app.route('/student/join', methods=['GET', 'POST'])
@login_required
@student_required
def join_exam():
    if request.method == 'POST':
        exam_name = request.form.get('exam_name', '').strip()
        password = request.form.get('password', '').strip()
        conn = get_db()
        
        exam_data = conn.execute('''
            SELECT e.*, u.college_name as examiner_college 
            FROM exams e 
            JOIN users u ON e.examiner_id = u.id 
            WHERE e.exam_name = ? AND e.random_password = ? AND e.is_deleted = 0
        ''', (exam_name, password)).fetchone()
        
        if not exam_data:
            conn.close()
            flash('Invalid Credentials.', 'error')
            return redirect(url_for('student_dashboard'))
        
        # ─── FIXED: Only block if actually submitted (submitted_at is NOT NULL) ───
# Change this logic in the join_exam function:
        existing_result = conn.execute(
            'SELECT total_questions FROM results WHERE student_id = ? AND exam_id = ?', 
                (session['user_id'], exam_data['id'])
            ).fetchone()

# ONLY block them if they have actually submitted questions
        if existing_result and existing_result['total_questions'] > 0:
            conn.close()
            flash('Security Alert: You have already submitted this exam.', 'error')
            return redirect(url_for('student_dashboard'))        
        if session.get('college') != exam_data['examiner_college']:
            conn.close()
            flash(f"Exam restricted to {exam_data['examiner_college']} students.", 'error')
            return redirect(url_for('student_dashboard'))
            
        # Create initial entry only if it doesn't exist
        try:
            conn.execute('INSERT INTO results (student_id, exam_id, score, total_questions) VALUES (?, ?, ?, ?)', 
                         (session['user_id'], exam_data['id'], 0, 0))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Record already exists (in_progress)

        conn.close()
        return redirect(url_for('take_exam', exam_id=exam_data['id']))
    
    return render_template('join_exam.html')

@app.route('/student/grades')
@login_required
@student_required
def student_grades():
    conn = get_db()
    # Updated query to check for results_published = 1
    raw_results = conn.execute('''
        SELECT e.exam_name, e.start_time, e.duration, r.score, r.total_questions, r.submitted_at 
        FROM results r 
        JOIN exams e ON r.exam_id = e.id 
        WHERE r.student_id = ? AND r.submitted_at IS NOT NULL AND e.results_published = 1
        ORDER BY r.submitted_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Optional: Count how many are still "Waiting for Publication"
    waiting_count = conn.execute('''
        SELECT COUNT(*) FROM results r JOIN exams e ON r.exam_id = e.id
        WHERE r.student_id = ? AND e.results_published = 0
    ''', (session['user_id'],)).fetchone()[0]
    
    conn.close()
    
    processed = []
    for r in raw_results:
        res = dict(r)
        res['percentage'] = (res['score'] / res['total_questions'] * 100) if res['total_questions'] > 0 else 0
        processed.append(res)
        
    return render_template('student_grades.html', results=processed, waiting=waiting_count)


# 🔥 ONLY THIS FUNCTION IS UPDATED
def parse_questions(folder):
    import re

    q_path = os.path.join(EXAM_FILES_DIR, folder, 'question.txt')
    a_path = os.path.join(EXAM_FILES_DIR, folder, 'answer.txt')

    if not os.path.exists(q_path):
        return [], []

    with open(q_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    questions = []
    current_q = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect question start (1., 2., etc.)
        if re.match(r'^\d+\.', line):
            if current_q:
                questions.append(current_q)
            current_q = {
                'text': re.sub(r'^\d+\.\s*', '', line),
                'options': []
            }

        # Detect options
        elif re.match(r'^[\(\[]?[A-Da-d][\)\.\s-]+', line):
            if current_q:
                letter = re.search(r'[A-Da-d]', line).group(0).upper()
                text = re.sub(r'^[\(\[]?[A-Da-d][\)\.\s-]+', '', line)
                current_q['options'].append(f"({letter}) {text}")

    if current_q:
        questions.append(current_q)

    # ✅ Answers
    answers = []
    if os.path.exists(a_path):
        with open(a_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(r'\b([A-Da-d])\b', line)
                if match:
                    answers.append(match.group(1).lower())

    return questions, answers

@app.route('/student/exam/<int:exam_id>')
@login_required
@student_required
def take_exam(exam_id):
    conn = get_db()
    
    # ─── FIXED: Allow entry if not yet submitted ───
    # Update the check in take_exam function:
    check = conn.execute(
        'SELECT total_questions FROM results WHERE student_id = ? AND exam_id = ?',
        (session['user_id'], exam_id)
        ).fetchone()

# If total_questions is 0, it means they haven't submitted yet, so let them in
    if check and check['total_questions'] > 0:
        conn.close()
        flash('Exam already submitted.', 'error')
        return redirect(url_for('student_dashboard'))

    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    conn.close()
    
    if not exam: 
        return redirect(url_for('student_dashboard'))

    start_dt = safe_parse_dt(exam['start_time'])
    end_dt = start_dt + timedelta(minutes=exam['duration'])
    now = datetime.now()

    if now > end_dt:
        flash('The exam time has already expired.', 'error')
        return redirect(url_for('student_dashboard'))

    questions, _ = parse_questions(exam['exam_name'])
    
    return render_template('take_exam.html', 
                           exam=exam, 
                           questions=questions, 
                           start_time=start_dt.isoformat(),
                           end_time=end_dt.isoformat(),
                           server_now=now.isoformat())

@app.route('/student/submit/<int:exam_id>', methods=['POST'])
@login_required
@student_required
def submit_exam(exam_id):
    data = request.get_json()
    answers = data.get('answers', {})

    conn = get_db()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    
    if not exam:
        return jsonify({'error': 'Exam not found'}), 404

    # ✅ Get correct answers
    questions, correct_answers = parse_questions(exam['exam_name'])

    score = 0
    total = len(correct_answers)

    # ✅ Compare answers
    for i, correct in enumerate(correct_answers):
        user_ans = answers.get(str(i)) or answers.get(f"q{i}")

        if user_ans:
            # clean input like "(A)" → "a"
            user_ans = user_ans.strip().lower().replace("(", "").replace(")", "")
            
            if user_ans == correct.lower():
                score += 1

    # ✅ UPDATE RESULT (IMPORTANT)
    conn.execute('''
        UPDATE results 
        SET score = ?, total_questions = ?, submitted_at = CURRENT_TIMESTAMP
        WHERE student_id = ? AND exam_id = ?
    ''', (score, total, session['user_id'], exam_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

# ─── COMMON ROUTES ───────────────────────────────────────────

@app.route('/profile/update', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        cropped_data = request.form.get('cropped_image')
        if cropped_data and "," in cropped_data:
            try:
                encoded_data = cropped_data.split(",")[1]
                decoded_data = base64.b64decode(encoded_data)
                filename = secure_filename(f"user_{session['user_id']}.png")
                filepath = os.path.join(PROFILE_PICS_DIR, filename)
                with open(filepath, "wb") as f: f.write(decoded_data)
                conn = get_db()
                conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?', (filename, session['user_id']))
                conn.commit()
                conn.close()
                session['profile_pic'] = filename
                flash('Profile updated!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e: 
                flash(f'Error: {str(e)}', 'error')
    return render_template('update_profile.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
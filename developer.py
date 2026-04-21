from flask import Flask, render_template, redirect
import sqlite3

app = Flask(__name__)

DB_NAME = "exam_system.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# 🚀 DIRECT DASHBOARD (NO LOGIN)
@app.route('/')
def dashboard():
    conn = get_db()

    users = conn.execute("""
        SELECT * FROM users 
        WHERE role='admin' AND status='pending'
    """).fetchall()

    conn.close()

    return render_template('developer_dashboard.html', users=users)


# ✅ APPROVE
@app.route('/approve/<int:user_id>')
def approve(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET status='active' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect('/')


# ❌ REJECT
@app.route('/reject/<int:user_id>')
def reject(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET status='rejected' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True, port=5001)
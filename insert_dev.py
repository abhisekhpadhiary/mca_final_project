import sqlite3

# Path to your database file
DB_PATH = "exam_system.db"   # change path if your DB is in another folder

def insert_developer():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if developer already exists
        cursor.execute("SELECT * FROM users WHERE email = ?", ("abhisekhpadhiary@gmail.com",))
        existing_user = cursor.fetchone()

        if existing_user:
            print("Developer already exists in database ✅")
        else:
            # Insert developer user
            cursor.execute("""
                INSERT INTO users (username, email, password, role)
                VALUES (?, ?, ?, ?)
            """, ("Developer", "abhisekhpadhiary@gmail.com", "123456", "developer"))

            conn.commit()
            print("Developer inserted successfully ✅")

        conn.close()

    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    insert_developer()
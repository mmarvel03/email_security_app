import sqlite3
from datetime import datetime


def init_db():
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            subject TEXT,
            message TEXT,
            url TEXT,
            result TEXT,
            score INTEGER,
            created_at TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(analysis_history)")
    columns = [col[1] for col in cursor.fetchall()]

    if "message" not in columns:
        cursor.execute("ALTER TABLE analysis_history ADD COLUMN message TEXT")

    if "url" not in columns:
        cursor.execute("ALTER TABLE analysis_history ADD COLUMN url TEXT")

    if "created_at" not in columns:
        cursor.execute("ALTER TABLE analysis_history ADD COLUMN created_at TEXT")

    conn.commit()
    conn.close()


def save_analysis(sender, subject, message, url, result, score):
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO analysis_history (sender, subject, message, url, result, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sender, subject, message, url, result, score, created_at))

    conn.commit()
    conn.close()


def get_history():
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, sender, subject, result, score, created_at
        FROM analysis_history
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "sender": row[1],
            "subject": row[2],
            "result": row[3],
            "score": row[4],
            "created_at": row[5]
        })

    return history


def get_analysis_by_id(analysis_id):
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, sender, subject, message, url, result, score, created_at
        FROM analysis_history
        WHERE id = ?
    """, (analysis_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "sender": row[1],
        "subject": row[2],
        "message": row[3] or "",
        "url": row[4] or "",
        "result": row[5],
        "score": row[6],
        "created_at": row[7]
    }


def clear_history():
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM analysis_history")

    conn.commit()
    conn.close()

def is_duplicate_analysis(sender, subject, message, url, result, score):
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sender, subject, message, url, result, score
        FROM analysis_history
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        return False

    return (
        row[0] == sender and
        row[1] == subject and
        row[2] == message and
        row[3] == url and
        row[4] == result and
        row[5] == score
    )



def get_stats():
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM analysis_history")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analysis_history WHERE result = 'SAFE'")
    safe_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analysis_history WHERE result = 'SPAM'")
    spam_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analysis_history WHERE result = 'PHISHING'")
    phishing_count = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "safe": safe_count,
        "spam": spam_count,
        "phishing": phishing_count
    }
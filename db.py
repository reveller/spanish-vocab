import sqlite3
import json
import os

DATABASE_PATH = os.environ.get('DATABASE_PATH', '/data/vocab.db')

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS lessons (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            progress TEXT NOT NULL DEFAULT 'not_started',
            sort_order INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id TEXT NOT NULL,
            en TEXT NOT NULL,
            es TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()

def seed_from_json(json_path):
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
    if count > 0:
        conn.close()
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for i, lesson in enumerate(data['lessons']):
        conn.execute(
            "INSERT INTO lessons (id, title, progress, sort_order) VALUES (?, ?, ?, ?)",
            (lesson['id'], lesson['title'], lesson['progress'], i)
        )
        for j, word in enumerate(lesson['words']):
            conn.execute(
                "INSERT INTO words (lesson_id, en, es, sort_order) VALUES (?, ?, ?, ?)",
                (lesson['id'], word[0], word[1], j)
            )
    conn.commit()
    conn.close()

def get_all_lessons():
    conn = get_db()
    lessons = conn.execute("SELECT * FROM lessons ORDER BY sort_order").fetchall()
    result = []
    for lesson in lessons:
        words = conn.execute(
            "SELECT en, es FROM words WHERE lesson_id = ? ORDER BY sort_order",
            (lesson['id'],)
        ).fetchall()
        result.append({
            'id': lesson['id'],
            'title': lesson['title'],
            'progress': lesson['progress'],
            'words': [[w['en'], w['es']] for w in words]
        })
    conn.close()
    return result

def add_lesson(title):
    conn = get_db()
    row = conn.execute("SELECT MAX(CAST(SUBSTR(id, 2) AS INTEGER)) FROM lessons").fetchone()
    next_num = (row[0] or 0) + 1
    new_id = f"L{next_num}"
    sort_order_row = conn.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM lessons").fetchone()
    sort_order = sort_order_row[0]
    conn.execute(
        "INSERT INTO lessons (id, title, progress, sort_order) VALUES (?, ?, 'not_started', ?)",
        (new_id, title, sort_order)
    )
    conn.commit()
    conn.close()
    return {'id': new_id, 'title': title, 'progress': 'not_started', 'words': []}

def update_lesson_progress(lesson_id, progress):
    conn = get_db()
    cursor = conn.execute(
        "UPDATE lessons SET progress = ? WHERE id = ?",
        (progress, lesson_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def delete_lesson(lesson_id):
    conn = get_db()
    conn.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    conn.commit()
    conn.close()

def add_word(lesson_id, en, es):
    conn = get_db()
    exists = conn.execute("SELECT 1 FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if not exists:
        conn.close()
        return False
    sort_order_row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM words WHERE lesson_id = ?",
        (lesson_id,)
    ).fetchone()
    conn.execute(
        "INSERT INTO words (lesson_id, en, es, sort_order) VALUES (?, ?, ?, ?)",
        (lesson_id, en, es, sort_order_row[0])
    )
    conn.commit()
    conn.close()
    return True

def delete_word(lesson_id, word_index):
    conn = get_db()
    word = conn.execute(
        "SELECT id FROM words WHERE lesson_id = ? ORDER BY sort_order LIMIT 1 OFFSET ?",
        (lesson_id, word_index)
    ).fetchone()
    if not word:
        conn.close()
        return False
    conn.execute("DELETE FROM words WHERE id = ?", (word['id'],))
    # Re-number sort_order to keep indices contiguous
    remaining = conn.execute(
        "SELECT id FROM words WHERE lesson_id = ? ORDER BY sort_order",
        (lesson_id,)
    ).fetchall()
    for i, row in enumerate(remaining):
        conn.execute("UPDATE words SET sort_order = ? WHERE id = ?", (i, row['id']))
    conn.commit()
    conn.close()
    return True

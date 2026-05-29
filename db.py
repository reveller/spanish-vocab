import sqlite3
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

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
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
    """)
    existing_cols = {row['name'] for row in conn.execute("PRAGMA table_info(words)").fetchall()}
    for col in ('example', 'note', 'region'):
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE words ADD COLUMN {col} TEXT")
    conn.commit()
    conn.close()

def seed_user(email, password):
    conn = get_db()
    exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, generate_password_hash(password))
        )
        conn.commit()
    conn.close()

def authenticate_user(email, password):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        return {'id': user['id'], 'email': user['email']}
    return None

def _normalize_word(word):
    """Accept either [en, es] tuple form or {en, es, example, note, region} object."""
    if isinstance(word, list):
        return {'en': word[0], 'es': word[1], 'example': None, 'note': None, 'region': None}
    return {
        'en': word['en'],
        'es': word['es'],
        'example': word.get('example'),
        'note': word.get('note'),
        'region': word.get('region'),
    }

def seed_from_json(json_path):
    """Seed empty DB or enrich existing rows with example/note/region from JSON.

    Behavior:
      - Fresh DB (no lessons): full insert.
      - Pre-enrichment DB (has lessons but no word has example/note/region populated):
        wipe and rebuild the words table. Lesson rows and their `progress` are
        preserved — only word content is regenerated.
      - Already-enriched DB: safe enrich pass. Match each JSON word by
        (lesson_id, es); update if found, insert if not. Existing rows with no
        match are left untouched (could be user-added).
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    conn = get_db()

    has_lessons = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0] > 0
    has_enrichment = False
    if has_lessons:
        has_enrichment = conn.execute(
            "SELECT 1 FROM words WHERE example IS NOT NULL OR note IS NOT NULL OR region IS NOT NULL LIMIT 1"
        ).fetchone() is not None

    rebuild_mode = has_lessons and not has_enrichment
    if rebuild_mode:
        conn.execute("DELETE FROM words")

    for i, lesson in enumerate(data['lessons']):
        existing = conn.execute("SELECT id FROM lessons WHERE id = ?", (lesson['id'],)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO lessons (id, title, progress, sort_order) VALUES (?, ?, ?, ?)",
                (lesson['id'], lesson['title'], lesson.get('progress', 'not_started'), i)
            )

        if rebuild_mode or not existing:
            for j, raw_word in enumerate(lesson['words']):
                w = _normalize_word(raw_word)
                conn.execute(
                    "INSERT INTO words (lesson_id, en, es, example, note, region, sort_order) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (lesson['id'], w['en'], w['es'], w['example'], w['note'], w['region'], j)
                )
            continue

        # Enrich pass: match by (lesson_id, es). Track claimed ids in case of
        # duplicate es within a lesson.
        claimed = set()
        for j, raw_word in enumerate(lesson['words']):
            w = _normalize_word(raw_word)
            candidates = conn.execute(
                "SELECT id FROM words WHERE lesson_id = ? AND es = ? ORDER BY sort_order",
                (lesson['id'], w['es'])
            ).fetchall()
            row = next((r for r in candidates if r['id'] not in claimed), None)
            if row:
                claimed.add(row['id'])
                conn.execute(
                    "UPDATE words SET en = ?, example = ?, note = ?, region = ?, sort_order = ? WHERE id = ?",
                    (w['en'], w['example'], w['note'], w['region'], j, row['id'])
                )
            else:
                conn.execute(
                    "INSERT INTO words (lesson_id, en, es, example, note, region, sort_order) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (lesson['id'], w['en'], w['es'], w['example'], w['note'], w['region'], j)
                )
    conn.commit()
    conn.close()

def get_all_lessons():
    conn = get_db()
    lessons = conn.execute("SELECT * FROM lessons ORDER BY sort_order").fetchall()
    result = []
    for lesson in lessons:
        words = conn.execute(
            "SELECT en, es, example, note, region FROM words WHERE lesson_id = ? ORDER BY sort_order",
            (lesson['id'],)
        ).fetchall()
        result.append({
            'id': lesson['id'],
            'title': lesson['title'],
            'progress': lesson['progress'],
            'words': [{
                'en': w['en'],
                'es': w['es'],
                'example': w['example'],
                'note': w['note'],
                'region': w['region'],
            } for w in words]
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

def add_word(lesson_id, en, es, example=None, note=None, region=None):
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
        "INSERT INTO words (lesson_id, en, es, example, note, region, sort_order) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (lesson_id, en, es, example, note, region, sort_order_row[0])
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

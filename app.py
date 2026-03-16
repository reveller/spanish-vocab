from flask import Flask, jsonify, request, send_from_directory, session, redirect
from functools import wraps
import logging
import os
from db import init_db, seed_from_json, seed_user, authenticate_user
from db import get_all_lessons, add_lesson as db_add_lesson
from db import update_lesson_progress, delete_lesson as db_delete_lesson
from db import add_word as db_add_word, delete_word as db_delete_word

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger('vocab')

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

SEED_FILE = os.path.join(os.path.dirname(__file__), 'lessons.json')

init_db()
seed_email = os.environ.get('SEED_USER_EMAIL')
seed_pass = os.environ.get('SEED_USER_PASSWORD')
if seed_email and seed_pass:
    seed_user(seed_email, seed_pass)
if os.path.exists(SEED_FILE):
    seed_from_json(SEED_FILE)

def client_ip():
    return request.headers.get('X-Real-IP', request.remote_addr)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            log.warning('Unauthorized API access: %s %s from %s',
                        request.method, request.path, client_ip())
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    if 'user_id' not in session:
        return send_from_directory('static', 'login.html')
    return send_from_directory('static', 'index.html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/login', methods=['POST'])
def login():
    body = request.json
    email = body.get('email', '')
    user = authenticate_user(email, body.get('password', ''))
    if user:
        session['user_id'] = user['id']
        session['email'] = user['email']
        log.info('Login success: %s from %s', email, client_ip())
        return jsonify({'ok': True})
    log.warning('Login failed: %s from %s', email, client_ip())
    return jsonify({'error': 'Invalid email or password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    email = session.get('email', 'unknown')
    session.clear()
    log.info('Logout: %s from %s', email, client_ip())
    return jsonify({'ok': True})

@app.route('/api/lessons', methods=['GET'])
@login_required
def get_lessons():
    return jsonify({'lessons': get_all_lessons()})

@app.route('/api/lessons', methods=['POST'])
@login_required
def add_lesson():
    body = request.json
    lesson = db_add_lesson(body['title'])
    log.info('Lesson created: %s "%s" by %s', lesson['id'], body['title'], session.get('email'))
    return jsonify(lesson), 201

@app.route('/api/lessons/<lesson_id>/progress', methods=['PUT'])
@login_required
def update_progress(lesson_id):
    body = request.json
    if update_lesson_progress(lesson_id, body['progress']):
        return jsonify({'ok': True, 'progress': body['progress']})
    return jsonify({'error': 'Lesson not found'}), 404

@app.route('/api/lessons/<lesson_id>/words', methods=['POST'])
@login_required
def add_word(lesson_id):
    body = request.json
    if db_add_word(lesson_id, body['en'], body['es']):
        log.info('Word added: "%s" → "%s" in %s by %s',
                 body['en'], body['es'], lesson_id, session.get('email'))
        return jsonify({'ok': True}), 201
    return jsonify({'error': 'Lesson not found'}), 404

@app.route('/api/lessons/<lesson_id>/words/<int:word_index>', methods=['DELETE'])
@login_required
def delete_word(lesson_id, word_index):
    if db_delete_word(lesson_id, word_index):
        log.info('Word deleted: index %d in %s by %s',
                 word_index, lesson_id, session.get('email'))
        return jsonify({'ok': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/lessons/<lesson_id>', methods=['DELETE'])
@login_required
def delete_lesson(lesson_id):
    db_delete_lesson(lesson_id)
    log.info('Lesson deleted: %s by %s', lesson_id, session.get('email'))
    return jsonify({'ok': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, port=port)

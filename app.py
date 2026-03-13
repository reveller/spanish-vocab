from flask import Flask, jsonify, request, send_from_directory
import os
from db import init_db, seed_from_json, get_all_lessons, add_lesson as db_add_lesson
from db import update_lesson_progress, delete_lesson as db_delete_lesson
from db import add_word as db_add_word, delete_word as db_delete_word

app = Flask(__name__, static_folder='static')

SEED_FILE = os.path.join(os.path.dirname(__file__), 'lessons.json')

init_db()
if os.path.exists(SEED_FILE):
    seed_from_json(SEED_FILE)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/lessons', methods=['GET'])
def get_lessons():
    return jsonify({'lessons': get_all_lessons()})

@app.route('/api/lessons', methods=['POST'])
def add_lesson():
    body = request.json
    lesson = db_add_lesson(body['title'])
    return jsonify(lesson), 201

@app.route('/api/lessons/<lesson_id>/progress', methods=['PUT'])
def update_progress(lesson_id):
    body = request.json
    if update_lesson_progress(lesson_id, body['progress']):
        return jsonify({'ok': True, 'progress': body['progress']})
    return jsonify({'error': 'Lesson not found'}), 404

@app.route('/api/lessons/<lesson_id>/words', methods=['POST'])
def add_word(lesson_id):
    body = request.json
    if db_add_word(lesson_id, body['en'], body['es']):
        return jsonify({'ok': True}), 201
    return jsonify({'error': 'Lesson not found'}), 404

@app.route('/api/lessons/<lesson_id>/words/<int:word_index>', methods=['DELETE'])
def delete_word(lesson_id, word_index):
    if db_delete_word(lesson_id, word_index):
        return jsonify({'ok': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/lessons/<lesson_id>', methods=['DELETE'])
def delete_lesson(lesson_id):
    db_delete_lesson(lesson_id)
    return jsonify({'ok': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, port=port)

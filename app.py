from flask import Flask, jsonify, request, send_from_directory
import json, os

app = Flask(__name__, static_folder='static')
DATA_FILE = os.path.join(os.path.dirname(__file__), 'lessons.json')

def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/lessons', methods=['GET'])
def get_lessons():
    data = load_data()
    return jsonify(data)

@app.route('/api/next_lesson', methods=['GET'])
def get_next_lesson():
    data = load_data()
    return jsonify({"next_lesson": data["next_lesson"]})

@app.route('/api/next_lesson', methods=['PUT'])
def update_next_lesson():
    data = load_data()
    body = request.json
    data["next_lesson"] = body["next_lesson"]
    save_data(data)
    return jsonify({"next_lesson": data["next_lesson"]})

@app.route('/api/lessons', methods=['POST'])
def add_lesson():
    data = load_data()
    lessons = data["lessons"]
    body = request.json
    new_id = f"L{len(lessons) + 1}"
    lesson = {"id": new_id, "title": body['title'], "words": []}
    lessons.append(lesson)
    save_data(data)
    return jsonify(lesson), 201

@app.route('/api/lessons/<lesson_id>/words', methods=['POST'])
def add_word(lesson_id):
    data = load_data()
    body = request.json
    for lesson in data["lessons"]:
        if lesson['id'] == lesson_id:
            lesson['words'].append([body['en'], body['es']])
            save_data(data)
            return jsonify({'ok': True}), 201
    return jsonify({'error': 'Lesson not found'}), 404

@app.route('/api/lessons/<lesson_id>/words/<int:word_index>', methods=['DELETE'])
def delete_word(lesson_id, word_index):
    data = load_data()
    for lesson in data["lessons"]:
        if lesson['id'] == lesson_id:
            if 0 <= word_index < len(lesson['words']):
                lesson['words'].pop(word_index)
                save_data(data)
                return jsonify({'ok': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/lessons/<lesson_id>', methods=['DELETE'])
def delete_lesson(lesson_id):
    data = load_data()
    data["lessons"] = [l for l in data["lessons"] if l['id'] != lesson_id]
    save_data(data)
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(debug=True, port=5050)

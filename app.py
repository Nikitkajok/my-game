from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DATABASE = 'game.db'

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rating INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0
            )
        ''')
        db.commit()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Имя и пароль обязательны"}), 400
    hashed = hash_password(password)
    try:
        with get_db() as db:
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
            db.commit()
        return jsonify({"message": "Пользователь создан"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Это имя уже занято"}), 409

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    hashed = hash_password(password)
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, hashed)).fetchone()
    if user:
        return jsonify({
            "message": "Успешный вход",
            "username": user['username'],
            "rating": user['rating'],
            "wins": user['wins'],
            "losses": user['losses'],
            "draws": user['draws']
        })
    return jsonify({"error": "Неверное имя или пароль"}), 401

@app.route('/api/stats', methods=['POST'])
def update_stats():
    data = request.json
    username = data.get('username')
    outcome = data.get('outcome')
    diff = data.get('difficulty', 'medium')
    
    points = 0
    if outcome == 'win': points = 10 if diff == 'easy' else 30 if diff == 'medium' else 100
    elif outcome == 'draw': points = 5

    with get_db() as db:
        if outcome == 'win':
            db.execute("UPDATE users SET wins = wins + 1, rating = rating + ? WHERE username = ?", (points, username))
        elif outcome == 'lose':
            db.execute("UPDATE users SET losses = losses + 1 WHERE username = ?", (username,))
        elif outcome == 'draw':
            db.execute("UPDATE users SET draws = draws + 1, rating = rating + ? WHERE username = ?", (points, username))
        db.commit()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return jsonify({"rating": user['rating'], "wins": user['wins'], "losses": user['losses'], "draws": user['draws']})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
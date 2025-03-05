from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import os
import sqlite3
import jwt
import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import hashlib
import random
import string

# Flask App Configuration
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "BigBlackBalls.exe")  # Change this in production
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["DATABASE"] = "storage.db"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Database Helper Functions
def get_db_connection():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row  # Allows access to columns by name
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )''')
        conn.commit()

def add_user(username, password):
    hashed_password = generate_password_hash(password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()

def get_user(username):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()

def add_file(filename, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO files (filename, user_id) VALUES (?, ?)", (filename, user_id))
        conn.commit()

def get_user_files(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM files WHERE user_id = ?", (user_id,))
        return [row[0] for row in cursor.fetchall()]

# Ensure the admin user exists
def ensure_admin():
    user = get_user("admin")
    if not user:
        add_user("admin", "admin")  # Default credentials: admin / admin

# JWT Authentication Middleware
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get("token")
        if not token:
            flash("You need to log in first!", "danger")
            return redirect(url_for("login"))

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            session["user"] = data["username"]
        except jwt.ExpiredSignatureError:
            flash("Session expired. Please log in again.", "danger")
            return redirect(url_for("login"))
        except jwt.InvalidTokenError:
            flash("Invalid token. Please log in again.", "danger")
            return redirect(url_for("login"))

        return f(*args, **kwargs)
    return decorated

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user(username)

        if user and check_password_hash(user['password'], password):
            token = jwt.encode({
                "username": username, 
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }, app.config["SECRET_KEY"], algorithm="HS256")
            session["token"] = token
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials!", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('token', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@token_required
def dashboard():
    user = get_user(session["user"])
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            add_file(filename, user['id'])
            flash("File uploaded successfully!", "success")

    files = get_user_files(user['id'])
    return render_template('dashboard.html', username=session["user"], files=files)

@app.route('/download/<filename>')
@token_required
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == '__main__':
    init_db()
    ensure_admin()
    app.run(debug=True, host='0.0.0.0')

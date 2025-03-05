import os
import sqlite3
import jwt
import datetime
import json
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Flask App Configuration
app = Flask(__name__)

# You can set this in your environment variables for added security in production
app.config["SECRET_KEY"] = os.getenv('SECRET_KEY', 'supersecretkey')  # Set this in the environment
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")  # Ensuring cross-platform compatibility
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

DATABASE = "storage.db"
USERS_JSON_FILE = os.path.join(os.getcwd(), "users.json")  # Cross-platform path

# Initialize Database and Users JSON
def init_db():
    # Check if users JSON file exists, create it with admin user if not
    if not os.path.exists(USERS_JSON_FILE):
        with open(USERS_JSON_FILE, 'w') as f:
            users_data = {
                "admin": {
                    "username": "admin",
                    "password": generate_password_hash("admin")  # Hash the default password
                }
            }
            json.dump(users_data, f)
    
    # SQLite database initialization code
    with sqlite3.connect(DATABASE) as conn:
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

# Database Helpers
def get_user(username):
    # First, check the SQLite database
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            return user

    # If the user is not found in the SQLite DB, check the users JSON file
    if os.path.exists(USERS_JSON_FILE):
        with open(USERS_JSON_FILE, 'r') as f:
            users_data = json.load(f)
            user_data = users_data.get(username)
            if user_data:
                return (None, user_data["username"], user_data["password"])
    
    return None

def add_user(username, password):
    hashed_password = generate_password_hash(password)
    
    # First, add to SQLite database
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
    
    # Now add to the JSON file as well
    if os.path.exists(USERS_JSON_FILE):
        with open(USERS_JSON_FILE, 'r+') as f:
            users_data = json.load(f)
            users_data[username] = {
                "username": username,
                "password": hashed_password
            }
            f.seek(0)
            json.dump(users_data, f)

def add_file(filename, user_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO files (filename, user_id) VALUES (?, ?)", (filename, user_id))
        conn.commit()

def get_user_files(user_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM files WHERE user_id = ?", (user_id,))
        return [row[0] for row in cursor.fetchall()]

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
        except:
            flash("Invalid session. Please log in again.", "danger")
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

        if user and check_password_hash(user[2], password):
            # Use the correct syntax for PyJWT 2.x
            token = jwt.encode(
                {"username": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)},
                app.config["SECRET_KEY"],
                algorithm="HS256"
            )
            session["token"] = token
            print("user logged in")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials!", "danger")
            print("User auth failed")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if get_user(username):
            flash("Username already exists!", "danger")
        else:
            add_user(username, password)
            flash("Account created! You can now log in.", "success")
            return redirect(url_for('login'))

    return render_template('register.html')

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
            add_file(filename, user[0])
            flash("File uploaded successfully!", "success")

    files = get_user_files(user[0])
    return render_template('dashboard.html', username=session["user"], files=files)

@app.route('/download/<filename>')
@token_required
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == '__main__':
    init_db()  # Initialize the database and check for users JSON file
    app.run(debug=True, host='0.0.0.0')

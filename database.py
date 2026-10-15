"""Store user accounts and their essay projects in a small SQLite database.

SQLite keeps the whole database in one file (instance/researchify.db), so there's
no separate database server to set up. Git ignores the instance folder, so nobody's
account ends up on GitHub.
"""

import hashlib
import json
import os
import secrets
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

DATABASE = os.path.join(os.path.dirname(__file__), "instance", "researchify.db")


def connect():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    # Lets us read columns by name, like row["email"].
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Failed log-ins, so someone can't keep guessing a password.
        db.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY,
                key TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Password reset links. Only a hash of each link's secret is stored, like a password.
        db.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Each user's projects are saved together as one block of JSON text,
        # the same shape the page already uses in the browser.
        db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def create_user(name, email, password):
    """Add a user and return their ID, or None if the email is already registered."""
    # Never store the password itself, only a salted hash of it. Even if someone
    # copied the database, they couldn't read anyone's password.
    password_hash = generate_password_hash(password)
    try:
        with connect() as db:
            cursor = db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email.lower(), password_hash),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def check_login(email, password):
    """Return the user if the email and password match, otherwise None."""
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def get_user(user_id):
    with connect() as db:
        return db.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()


def load_projects(user_id):
    """Return the user's projects as a list, or None if they haven't saved any yet."""
    with connect() as db:
        row = db.execute("SELECT data FROM projects WHERE user_id = ?", (user_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def save_projects(user_id, projects):
    with connect() as db:
        db.execute(
            """
            INSERT INTO projects (user_id, data) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET data = excluded.data, updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, json.dumps(projects)),
        )


# ---------- Limiting log-in attempts ----------

def record_attempt(key):
    """Note one attempt, e.g. key "login-email:ada@example.com" or "login-ip:1.2.3.4"."""
    with connect() as db:
        db.execute("INSERT INTO login_attempts (key) VALUES (?)", (key,))
        # Old attempts don't matter any more, so tidy them away.
        db.execute("DELETE FROM login_attempts WHERE created_at < datetime('now', '-1 day')")


def recent_attempts(key, minutes):
    """How many attempts with this key happened in the last few minutes."""
    with connect() as db:
        row = db.execute(
            "SELECT COUNT(*) AS count FROM login_attempts WHERE key = ? AND created_at > datetime('now', ?)",
            (key, "-" + str(minutes) + " minutes"),
        ).fetchone()
    return row["count"]


def clear_attempts(key):
    with connect() as db:
        db.execute("DELETE FROM login_attempts WHERE key = ?", (key,))


# ---------- Resetting a forgotten password ----------

def find_user_by_email(email):
    with connect() as db:
        return db.execute("SELECT id, name, email FROM users WHERE email = ?", (email.lower(),)).fetchone()


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_reset_token(user_id):
    """Make a one-use reset link secret that works for 1 hour, and return it."""
    token = secrets.token_urlsafe(32)
    with connect() as db:
        db.execute(
            "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES (?, ?, datetime('now', '+1 hour'))",
            (user_id, hash_token(token)),
        )
    return token


def check_reset_token(token):
    """Return the user ID if the token is real, unused and not expired, otherwise None."""
    with connect() as db:
        row = db.execute(
            "SELECT user_id FROM password_resets WHERE token_hash = ? AND used = 0 AND expires_at > datetime('now')",
            (hash_token(token),),
        ).fetchone()
    return row["user_id"] if row else None


def reset_password(token, new_password):
    """Set a new password using a reset token. Returns True if it worked."""
    user_id = check_reset_token(token)
    if not user_id:
        return False
    with connect() as db:
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_password), user_id))
        # Once the password changes, every reset link for this account stops working.
        db.execute("UPDATE password_resets SET used = 1 WHERE user_id = ?", (user_id,))
        # And the student can log in straight away, even if they were locked out.
        email = db.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()["email"]
        db.execute("DELETE FROM login_attempts WHERE key = ?", ("login-email:" + email,))
    return True

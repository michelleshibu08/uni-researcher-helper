"""Store user accounts and their essay projects in a small SQLite database.

SQLite keeps the whole database in one file (instance/researchify.db), so there's
no separate database server to set up. Git ignores the instance folder, so nobody's
account ends up on GitHub.
"""

import json
import os
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

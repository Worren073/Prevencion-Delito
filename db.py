import os
import logging
from functools import wraps
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

TURSO_URL = os.getenv("TURSO_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

_conn = None

def get_conn():
    global _conn
    if _conn is not None:
        return _conn
    if TURSO_URL:
        import libsql_experimental as libsql
        _conn = libsql.connect(
            "/app/data/users.db",
            sync_url=TURSO_URL,
            auth_token=TURSO_AUTH_TOKEN,
            sync_interval=5,
        )
    else:
        import sqlite3
        _conn = sqlite3.connect("/app/data/users.db", check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    _init_schema()
    return _conn

def close_conn():
    global _conn
    if _conn is not None:
        try:
            if TURSO_URL:
                _conn.sync()
            _conn.close()
        except Exception:
            pass
        _conn = None

def _init_schema():
    conn = _conn
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'worker',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    if TURSO_URL:
        conn.sync()

def _with_retry(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as e:
            if "Hrana" in str(e) or "stream" in str(e):
                close_conn()
                return fn(*args, **kwargs)
            raise
    return wrapper

@_with_retry
def get_user_by_email(email):
    rows = get_conn().execute(
        "SELECT id, email, password_hash, name, role, active FROM users WHERE email = ? AND active = 1",
        (email,)
    ).fetchall()
    if rows:
        r = rows[0]
        return {"id": r[0], "email": r[1], "password_hash": r[2], "name": r[3], "role": r[4], "active": r[5]}
    return None

@_with_retry
def list_users():
    rows = get_conn().execute(
        "SELECT id, email, name, role, active, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    return [{"id": r[0], "email": r[1], "name": r[2], "role": r[3], "active": r[4], "created_at": r[5]} for r in rows]

@_with_retry
def create_user(email, password, name, role):
    conn = get_conn()
    pw_hash = generate_password_hash(password)
    conn.execute(
        "INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
        (email, pw_hash, name, role)
    )
    if TURSO_URL:
        conn.sync()

@_with_retry
def update_user(user_id, email=None, password=None, name=None, role=None, active=None):
    conn = get_conn()
    sets = []
    params = []
    if email is not None:
        sets.append("email = ?"); params.append(email)
    if password is not None:
        sets.append("password_hash = ?"); params.append(generate_password_hash(password))
    if name is not None:
        sets.append("name = ?"); params.append(name)
    if role is not None:
        sets.append("role = ?"); params.append(role)
    if active is not None:
        sets.append("active = ?"); params.append(1 if active else 0)
    if not sets:
        return
    sets.append("updated_at = datetime('now')")
    params.append(user_id)
    conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
    if TURSO_URL:
        conn.sync()

@_with_retry
def delete_user(user_id):
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    if TURSO_URL:
        conn.sync()

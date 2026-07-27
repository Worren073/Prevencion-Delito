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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS actividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_actividad TEXT NOT NULL,
            funcionario TEXT NOT NULL,
            tipo_actividad TEXT NOT NULL,
            lugar TEXT NOT NULL,
            funcionarios_count INTEGER NOT NULL DEFAULT 0,
            novedades TEXT DEFAULT '',
            estatus TEXT NOT NULL DEFAULT 'En Proceso',
            solicitud_ref TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solicitante TEXT NOT NULL,
            telefono TEXT NOT NULL,
            tipo_entidad TEXT NOT NULL,
            comunidad TEXT NOT NULL,
            parroquia TEXT NOT NULL,
            tema TEXT NOT NULL,
            fecha_actividad TEXT DEFAULT '',
            asistentes INTEGER DEFAULT 0,
            publico TEXT DEFAULT '',
            estatus TEXT NOT NULL DEFAULT 'pendiente',
            motivo TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    try:
        conn.execute("ALTER TABLE solicitudes ADD COLUMN motivo TEXT DEFAULT ''")
    except Exception:
        pass
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
    conn.commit()
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
    conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", tuple(params))
    conn.commit()
    if TURSO_URL:
        conn.sync()

@_with_retry
def delete_user(user_id):
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    if TURSO_URL:
        conn.sync()

# ---------------------------------------------------------------------------
# Actividades CRUD
# ---------------------------------------------------------------------------

@_with_retry
def create_actividad(fecha_actividad, funcionario, tipo_actividad, lugar, funcionarios_count, novedades, estatus="En Proceso", solicitud_ref=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO actividades (fecha_actividad, funcionario, tipo_actividad, lugar, funcionarios_count, novedades, estatus, solicitud_ref) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (fecha_actividad, funcionario, tipo_actividad, lugar, funcionarios_count, novedades, estatus, solicitud_ref)
    )
    conn.commit()
    if TURSO_URL:
        conn.sync()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

@_with_retry
def update_actividad_status(actividad_id, estatus):
    conn = get_conn()
    conn.execute("UPDATE actividades SET estatus = ?, updated_at = datetime('now') WHERE id = ?", (estatus, actividad_id))
    conn.commit()
    if TURSO_URL:
        conn.sync()

@_with_retry
def list_actividades_turso():
    rows = get_conn().execute(
        "SELECT id, fecha_actividad, funcionario, tipo_actividad, lugar, funcionarios_count, novedades, estatus, solicitud_ref, created_at FROM actividades ORDER BY created_at DESC"
    ).fetchall()
    return [{"id": r[0], "fecha_actividad": r[1], "funcionario": r[2], "tipo_actividad": r[3], "lugar": r[4], "funcionarios_count": r[5], "novedades": r[6], "estatus": r[7], "solicitud_ref": r[8], "created_at": r[9]} for r in rows]

# ---------------------------------------------------------------------------
# Solicitudes CRUD
# ---------------------------------------------------------------------------

@_with_retry
def create_solicitud(solicitante, telefono, tipo_entidad, comunidad, parroquia, tema, fecha_actividad="", asistentes=0, publico=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO solicitudes (solicitante, telefono, tipo_entidad, comunidad, parroquia, tema, fecha_actividad, asistentes, publico) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (solicitante, telefono, tipo_entidad, comunidad, parroquia, tema, fecha_actividad, asistentes, publico)
    )
    conn.commit()
    if TURSO_URL:
        conn.sync()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

@_with_retry
def update_solicitud_status(solicitud_id, estatus, motivo=""):
    conn = get_conn()
    conn.execute("UPDATE solicitudes SET estatus = ?, motivo = ?, updated_at = datetime('now') WHERE id = ?", (estatus, motivo, solicitud_id))
    conn.commit()
    if TURSO_URL:
        conn.sync()

@_with_retry
def list_solicitudes():
    rows = get_conn().execute(
        "SELECT id, solicitante, telefono, tipo_entidad, comunidad, parroquia, tema, fecha_actividad, asistentes, publico, estatus, motivo, created_at FROM solicitudes ORDER BY created_at DESC"
    ).fetchall()
    return [{"id": r[0], "solicitante": r[1], "telefono": r[2], "tipo_entidad": r[3], "comunidad": r[4], "parroquia": r[5], "tema": r[6], "fecha_actividad": r[7], "asistentes": r[8], "publico": r[9], "estatus": r[10], "motivo": r[11], "created_at": r[12]} for r in rows]

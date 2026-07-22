import os
import secrets
import csv
import io
import logging
from datetime import timedelta
import requests
from dotenv import load_dotenv
from flask import Flask, request, session, redirect, render_template, send_from_directory, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash
import db

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
if 'FLASK_SECRET_KEY' not in os.environ:
    print("WARNING: FLASK_SECRET_KEY not set. Using temporary random key. Sessions will not persist across restarts.")

limiter = Limiter(get_remote_address, app=app, default_limits=[], storage_uri="memory://")

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', '').strip().lower()
ADMIN_PASSWORD_HASHES = [h.strip() for h in os.getenv('ADMIN_PASSWORD_HASH', '').split(',') if h.strip()]

if not ADMIN_PASSWORD_HASHES:
    raise RuntimeError("ADMIN_PASSWORD_HASH no configurado en .env. Genera uno con: python -c \"from werkzeug.security import generate_password_hash; print(generate_password_hash('tu-password'))\"")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRDaQfeXK0O1DUvYR584z_9lcZNNIDuuIM09IwoGebqULR5Ut1l_DB2pkoep45mb697LSjzJOIMUnTD/pub?output=csv"

CSV_ACTIVIDADES_URL = "https://docs.google.com/spreadsheets/d/1lG90_0On4vvaQ_Jxr1DWuZfOmz_8Y78jUDf1xInWiY8/export?format=csv&gid=1794869360"

HEADER_MAP = {
    'Marca temporal': 'fecha_solicitud',
    'Nombre del Solicitante.': 'solicitante',
    'Teléfono de Contacto': 'telefono',
    'Tipo de Entidad': 'tipo_entidad',
    'Nombre de comunidad O Escuela.': 'comunidad',
    'Parroquia / Zona.': 'parroquia',
    'Tema de charla Solicitada.': 'tema',
    'Fecha Sugerida para la Actividad.': 'fecha_actividad',
    'Cantidad Estimada de Asistentes.': 'asistentes',
    '¿A qué público objetivo está dirigida la actividad?': 'publico',
}

HEADER_MAP_ACTIVIDADES = {
    'Marca temporal': 'fecha_registro',
    'Fecha de Actividad': 'fecha_actividad',
    'Tipo de Actividad': 'tipo_actividad',
    'Lugar / Comunidad / Sector': 'lugar',
    'Cantidad de funcionarios Desplegados': 'funcionarios',
    'Novedades / Resumen de la Actividad': 'novedades',
    'Estatus de la Actividad': 'estatus',
    'Nombre del funcionario Responsable': 'funcionario',
}

MES_NAMES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self';"
        "script-src 'self' https://www.gstatic.com https://www.google.com https://cdnjs.cloudflare.com https://fonts.googleapis.com 'unsafe-inline';"
        "style-src 'self' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://www.gstatic.com 'unsafe-inline';"
        "img-src 'self' data: https://www.gstatic.com;"
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://www.gstatic.com;"
        "connect-src 'self' https://docs.google.com;"
        "frame-src 'self';"
    )
    return response

# ---------------------------------------------------------------------------
# CSRF helpers
# ---------------------------------------------------------------------------

def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

def validate_csrf():
    return secrets.compare_digest(
        request.form.get('csrf_token', ''),
        session.get('csrf_token', '')
    )

# ---------------------------------------------------------------------------
# Public static files (built by Vite)
# ---------------------------------------------------------------------------

@app.route('/')
def serve_index():
    return send_from_directory(os.path.join(BASE_DIR, 'dist'), 'index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'dist', 'assets'), filename)

@app.route('/logo-gobierno.png')
def serve_logo():
    return send_from_directory(os.path.join(BASE_DIR, 'dist'), 'logo-gobierno.png')

@app.route('/hero-bg.webp')
def serve_hero():
    return send_from_directory(os.path.join(BASE_DIR, 'dist'), 'hero-bg.webp')

@app.route('/src/<path:filename>')
def serve_src(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'src'), filename)

# ---------------------------------------------------------------------------
# API: KPIs (public dashboard - aggregated data only)
# ---------------------------------------------------------------------------

@app.route('/api/kpis')
def api_kpis():
    try:
        res = requests.get(CSV_URL, timeout=15)
        res.raise_for_status()
        res.encoding = 'utf-8'
        reader = csv.DictReader(io.StringIO(res.text))
    except Exception:
        return jsonify({'error': 'No se pudieron obtener los datos.'}), 502

    rows = []
    for row in reader:
        if not row.get('Marca temporal', '').strip():
            continue
        obj = {}
        for raw_key, val in row.items():
            key = HEADER_MAP.get(raw_key.strip())
            if key:
                obj[key] = (val or '').strip()
        obj['asistentes'] = int(obj.get('asistentes', 0) or 0)
        rows.append(obj)

    total = len(rows)
    beneficiarios = sum(r['asistentes'] for r in rows)
    entidades = len({r.get('comunidad', '').lower() for r in rows if r.get('comunidad')})
    parroquias_count = len({r.get('parroquia', '').lower() for r in rows if r.get('parroquia')})

    def count_by(fn):
        counts = {}
        for r in rows:
            k = fn(r)
            if k:
                counts[k] = counts.get(k, 0) + 1
        return [{'label': k, 'count': v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]

    temas = count_by(lambda r: r.get('tema'))
    tipo_entidad = count_by(lambda r: r.get('tipo_entidad'))
    parroquias_data = count_by(lambda r: r.get('parroquia'))

    meses_counts = {}
    for r in rows:
        fecha = r.get('fecha_solicitud', '')
        if not fecha:
            continue
        parts = fecha.split(' ')
        date_parts = parts[0].split('/')
        if len(date_parts) < 3:
            continue
        month = date_parts[1].zfill(2)
        year = date_parts[2]
        key = f"{year}-{month}"
        if key not in meses_counts:
            try:
                label = f"{MES_NAMES[int(date_parts[1]) - 1]} {year}"
            except IndexError:
                label = key
            meses_counts[key] = {'label': label, 'count': 0}
        meses_counts[key]['count'] += 1
    meses = [meses_counts[k] for k in sorted(meses_counts.keys())]

    return jsonify({
        'total': total,
        'beneficiarios': beneficiarios,
        'entidades': entidades,
        'parroquias': parroquias_count,
        'temas': temas,
        'tipo_entidad': tipo_entidad,
        'meses': meses,
        'parroquias_data': parroquias_data,
    })

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(roles=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not session.get('user'):
                return redirect('/login')
            if roles and session['user'].get('role') not in roles:
                return jsonify({'error': 'No autorizado'}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes", methods=['POST'])
def login():
    if request.method == 'POST':
        ip = request.remote_addr
        if not validate_csrf():
            logger.warning(f"CSRF inválido desde {ip}")
            return render_template('admin_login.html', error=True, csrf_token=generate_csrf_token())
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # 1. Try Turso
        user = db.get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            session['user'] = {'id': user['id'], 'email': user['email'], 'name': user['name'], 'role': user['role']}
            session.permanent = True
            logger.info(f"Login exitoso (Turso) para '{email}' rol={user['role']} desde {ip}")
            return redirect('/login/dashboard')

        # 2. Fallback superadmin (env vars)
        if email == ADMIN_EMAIL and any(check_password_hash(h, password) for h in ADMIN_PASSWORD_HASHES):
            session['user'] = {'email': ADMIN_EMAIL, 'name': 'Administrador', 'role': 'admin', 'is_superadmin': True}
            session.permanent = True
            logger.info(f"Login exitoso (superadmin) desde {ip}")
            return redirect('/login/dashboard')

        logger.warning(f"Login fallido para '{email}' desde {ip}")
        return render_template('admin_login.html', error=True, csrf_token=generate_csrf_token())
    return render_template('admin_login.html', csrf_token=generate_csrf_token())

@app.route('/login/dashboard')
def admin_dashboard():
    if not session.get('user'):
        return redirect('/login')
    return render_template('admin.html')

@app.route('/api/admin/data')
def admin_data():
    if not session.get('user'):
        return jsonify({'error': 'No autorizado'}), 401
    try:
        res = requests.get(CSV_URL, timeout=15)
        res.raise_for_status()
        res.encoding = 'utf-8'
        reader = csv.DictReader(io.StringIO(res.text))
    except Exception:
        return jsonify({'error': 'No se pudieron obtener los datos.'}), 502
    rows = []
    for row in reader:
        if not row.get('Marca temporal', '').strip():
            continue
        obj = {}
        for raw_key, val in row.items():
            key = HEADER_MAP.get(raw_key.strip())
            if key:
                obj[key] = (val or '').strip()
        obj['asistentes'] = int(obj.get('asistentes', 0) or 0)
        rows.append(obj)
    return jsonify({'rows': rows, 'total': len(rows)})

@app.route('/api/admin/actividades')
def admin_actividades():
    if not session.get('user'):
        return jsonify({'error': 'No autorizado'}), 401
    try:
        res = requests.get(CSV_ACTIVIDADES_URL, timeout=15)
        res.raise_for_status()
        res.encoding = 'utf-8'
        reader = csv.DictReader(io.StringIO(res.text))
    except Exception:
        return jsonify({'error': 'No se pudieron obtener los datos.'}), 502
    rows = []
    for row in reader:
        if not row.get('Marca temporal', '').strip():
            continue
        obj = {}
        for raw_key, val in row.items():
            key = HEADER_MAP_ACTIVIDADES.get(raw_key.strip())
            if key:
                obj[key] = (val or '').strip()
        obj['funcionarios'] = int(obj.get('funcionarios', 0) or 0)
        rows.append(obj)
    completadas = sum(1 for r in rows if r.get('estatus', '').lower() == 'completado')
    en_proceso = sum(1 for r in rows if r.get('estatus', '').lower() == 'en proceso')
    total_funcionarios = sum(r['funcionarios'] for r in rows)
    return jsonify({
        'rows': rows,
        'total': len(rows),
        'completadas': completadas,
        'en_proceso': en_proceso,
        'total_funcionarios': total_funcionarios,
    })

@app.route('/api/admin/me')
def admin_me():
    if not session.get('user'):
        return jsonify({'error': 'No autorizado'}), 401
    return jsonify(session['user'])

# ---------------------------------------------------------------------------
# Admin: user management (admin only)
# ---------------------------------------------------------------------------

@app.route('/api/admin/users', methods=['GET', 'POST'])
def admin_users():
    if not session.get('user') or session['user'].get('role') not in ('admin', 'superadmin'):
        return jsonify({'error': 'No autorizado'}), 403
    if request.method == 'GET':
        return jsonify({'users': db.list_users()})
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    role = data.get('role', 'worker')
    if not email or not password or not name:
        return jsonify({'error': 'email, password y name son requeridos'}), 400
    if role not in ('admin', 'worker', 'visitor'):
        return jsonify({'error': 'Rol inválido'}), 400
    try:
        db.create_user(email, password, name, role)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': f'Error al crear usuario: {e}'}), 400

@app.route('/api/admin/users/<int:user_id>', methods=['PUT', 'DELETE'])
def admin_user(user_id):
    if not session.get('user') or session['user'].get('role') not in ('admin', 'superadmin'):
        return jsonify({'error': 'No autorizado'}), 403
    if request.method == 'DELETE':
        db.delete_user(user_id)
        return jsonify({'ok': True})
    data = request.get_json()
    db.update_user(user_id, email=data.get('email'), password=data.get('password'), name=data.get('name'), role=data.get('role'), active=data.get('active'))
    return jsonify({'ok': True})

@app.route('/login/logout')
def admin_logout():
    session.pop('user', None)
    return redirect('/')

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', '').lower() in ('1', 'true')
    app.run(host='0.0.0.0', port=5000, debug=debug)

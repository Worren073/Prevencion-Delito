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
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRDaQfeXK0O1DUvYR584z_9lcZNNIDuuIM09IwoGebqULR5Ut1l_DB2pkoep45mb697LSjzJOIMUnTD/pub?output=csv"

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
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin_auth'] = True
            session.permanent = True
            logger.info(f"Login exitoso desde {ip}")
            return redirect('/login/dashboard')
        logger.warning(f"Login fallido para '{email}' desde {ip}")
        return render_template('admin_login.html', error=True, csrf_token=generate_csrf_token())
    return render_template('admin_login.html', csrf_token=generate_csrf_token())

@app.route('/login/dashboard')
def admin_dashboard():
    if not session.get('admin_auth'):
        return redirect('/login')
    return render_template('admin.html')

@app.route('/api/admin/data')
def admin_data():
    if not session.get('admin_auth'):
        return jsonify({'error': 'No autorizado'}), 401
    try:
        res = requests.get(CSV_URL, timeout=15)
        res.raise_for_status()
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

@app.route('/login/logout')
def admin_logout():
    session.pop('admin_auth', None)
    return redirect('/login')

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', '').lower() in ('1', 'true')
    app.run(host='0.0.0.0', port=5000, debug=debug)

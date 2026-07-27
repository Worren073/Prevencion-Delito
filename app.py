import os
import secrets
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, request, session, redirect, render_template, send_from_directory, jsonify
from flask_limiter import Limiter

from werkzeug.security import check_password_hash, generate_password_hash
import db

# Initialize database schema on startup (idempotent)
db.get_conn()

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.getenv('RENDER', '').lower() == 'true'

app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
if 'FLASK_SECRET_KEY' not in os.environ:
    print("WARNING: FLASK_SECRET_KEY not set. Using temporary random key. Sessions will not persist across restarts.")

def _real_client_ip():
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'

limiter = Limiter(_real_client_ip, app=app, default_limits=[], storage_uri="memory://")

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', '').strip().lower()
ADMIN_PASSWORD_HASHES = [h.strip() for h in os.getenv('ADMIN_PASSWORD_HASH', '').split(',') if h.strip()]

if not ADMIN_PASSWORD_HASHES:
    raise RuntimeError("ADMIN_PASSWORD_HASH no configurado en .env. Genera uno con: python -c \"from werkzeug.security import generate_password_hash; print(generate_password_hash('tu-password'))\"")

SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
MAIL_FROM = os.getenv('MAIL_FROM', SMTP_USER)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
        "script-src 'self' https://www.gstatic.com https://www.google.com https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.jsdelivr.net 'unsafe-inline';"
        "style-src 'self' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://www.gstatic.com https://cdn.jsdelivr.net 'unsafe-inline';"
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
        rows = db.list_solicitudes()
    except Exception:
        return jsonify({'error': 'No se pudieron obtener los datos.'}), 502

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

    meses = {}
    for r in rows:
        fecha = r.get('created_at', '')
        if not fecha:
            continue
        month = fecha[:7]
        if month not in meses:
            parts = month.split('-')
            try:
                label = f"{MES_NAMES[int(parts[1]) - 1]} {parts[0]}"
            except (IndexError, ValueError):
                label = month
            meses[month] = {'label': label, 'count': 0}
        meses[month]['count'] += 1
    meses_list = [meses[k] for k in sorted(meses.keys())]

    return jsonify({
        'total': total,
        'beneficiarios': beneficiarios,
        'entidades': entidades,
        'parroquias': parroquias_count,
        'temas': temas,
        'tipo_entidad': tipo_entidad,
        'meses': meses_list,
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

@app.errorhandler(429)
def ratelimit_handler(e):
    verify_mode = session.get('pending_user') is not None
    tpl = 'admin_verify.html' if verify_mode else 'admin_login.html'
    error = 'Demasiados intentos. Espera 15 minutos.'
    mask = session.get('_2fa_email_mask', '')
    return render_template(tpl, error=error, csrf_token=generate_csrf_token(), email_mask=mask), 429

def _mask_email(email):
    at = email.find('@')
    if at > 1:
        return email[0] + '***' + email[at-1:at] + email[at:]
    return email

def _send_email_code(addr, code):
    subject = "Código de verificación - Prevención del Delito"
    body = f"Su código de verificación es: {code}\n\nVálido por 5 minutos.\n\nSi no solicitó este código, ignore este mensaje."
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = MAIL_FROM
        msg['To'] = addr
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
            logger.info(f"2FA code enviado a {_mask_email(addr)}")
        except Exception as e:
            logger.error(f"Error al enviar email 2FA a {_mask_email(addr)}: {e}")
            raise
    else:
        logger.info(f"2FA code (SMTP no configurado): {code} para {addr}")

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("3 per 15 minutes", methods=['POST'])
def login():
    if request.method == 'POST':
        ip = request.remote_addr
        if not validate_csrf():
            logger.warning(f"CSRF inválido desde {ip}")
            return render_template('admin_login.html', error='CSRF inválido. Intenta de nuevo.', csrf_token=generate_csrf_token())
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # 1. Try Turso — requiere 2FA por email
        user = db.get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            code = f"{secrets.randbelow(1000000):06d}"
            session['pending_user'] = {'id': user['id'], 'email': user['email'], 'name': user['name'], 'role': user['role']}
            session['_2fa_code'] = generate_password_hash(code)
            session['_2fa_expiry'] = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            session['_2fa_email_mask'] = _mask_email(user['email'])
            session.permanent = True
            _send_email_code(user['email'], code)
            logger.info(f"2FA code enviado a '{_mask_email(user['email'])}' desde {ip}")
            return redirect('/login/verify')

        # 2. Fallback superadmin (env vars) — sin 2FA
        if email == ADMIN_EMAIL and any(check_password_hash(h, password) for h in ADMIN_PASSWORD_HASHES):
            session['user'] = {'email': ADMIN_EMAIL, 'name': 'Administrador', 'role': 'admin', 'is_superadmin': True}
            session.permanent = True
            logger.info(f"Login exitoso (superadmin) desde {ip}")
            return redirect('/login/dashboard')

        logger.warning(f"Login fallido para '{email}' desde {ip}")
        return render_template('admin_login.html', error='Correo o contraseña incorrectos.', csrf_token=generate_csrf_token())
    return render_template('admin_login.html', csrf_token=generate_csrf_token())

@app.route('/login/verify', methods=['GET', 'POST'])
@limiter.limit("3 per 15 minutes", methods=['POST'])
def login_verify():
    pending = session.get('pending_user')
    if not pending:
        return redirect('/login')
    mask = session.get('_2fa_email_mask', '')
    if request.method == 'GET':
        return render_template('admin_verify.html', error='', csrf_token=generate_csrf_token(), email_mask=mask)
    if not validate_csrf():
        return render_template('admin_verify.html', error='CSRF inválido. Intenta de nuevo.', csrf_token=generate_csrf_token(), email_mask=mask)
    code_input = request.form.get('code', '').strip()
    expiry_str = session.get('_2fa_expiry', '')
    if expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.utcnow() > expiry:
                session.pop('pending_user', None)
                session.pop('_2fa_code', None)
                session.pop('_2fa_expiry', None)
                session.pop('_2fa_email_mask', None)
                logger.warning(f"2FA code expirado para {pending.get('email')} desde {request.remote_addr}")
                return render_template('admin_verify.html', error='El código ha expirado. Solicite uno nuevo.', csrf_token=generate_csrf_token(), email_mask=mask)
        except (ValueError, TypeError):
            pass
    stored_hash = session.get('_2fa_code', '')
    if stored_hash and check_password_hash(stored_hash, code_input):
        session['user'] = pending
        session.pop('pending_user', None)
        session.pop('_2fa_code', None)
        session.pop('_2fa_expiry', None)
        session.pop('_2fa_email_mask', None)
        logger.info(f"2FA exitoso para '{pending['email']}' desde {request.remote_addr}")
        return redirect('/login/dashboard')
    logger.warning(f"2FA fallido para '{pending.get('email')}' desde {request.remote_addr}")
    return render_template('admin_verify.html', error='Código incorrecto. Intente de nuevo.', csrf_token=generate_csrf_token(), email_mask=mask)

@app.route('/login/resend-code', methods=['POST'])
def login_resend_code():
    pending = session.get('pending_user')
    if not pending:
        return redirect('/login')
    code = f"{secrets.randbelow(1000000):06d}"
    session['_2fa_code'] = generate_password_hash(code)
    session['_2fa_expiry'] = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    _send_email_code(pending['email'], code)
    logger.info(f"2FA code reenviado a '{_mask_email(pending['email'])}' desde {request.remote_addr}")
    return redirect('/login/verify')

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
        rows = db.list_solicitudes()
        return jsonify({'rows': rows, 'total': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------------------------------------
# Public solicitud submission (replaces Google Forms)
# ---------------------------------------------------------------------------

@app.route('/api/solicitudes', methods=['POST'])
def public_solicitud():
    data = request.form
    solicitante = data.get('solicitante', '').strip()
    telefono = data.get('telefono', '').strip()
    tipo_entidad = data.get('tipo_entidad', '').strip()
    comunidad = data.get('comunidad', '').strip()
    parroquia = data.get('parroquia', '').strip()
    tema = data.get('tema', '').strip()
    fecha_actividad = data.get('fecha_actividad', '').strip()
    try:
        asistentes = int(data.get('asistentes', 0))
    except (ValueError, TypeError):
        asistentes = 0
    publico = data.get('publico', '').strip()

    required = [solicitante, telefono, tipo_entidad, comunidad, parroquia, tema]
    if not all(required):
        return jsonify({'error': 'Campos requeridos faltantes'}), 400

    try:
        db.create_solicitud(solicitante, telefono, tipo_entidad, comunidad, parroquia, tema, fecha_actividad, asistentes, publico)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/solicitudes/<int:sid>/status', methods=['PUT'])
def admin_solicitud_status(sid):
    if not session.get('user'):
        return jsonify({'error': 'No autorizado'}), 401
    if session['user'].get('role') not in ('admin', 'worker'):
        return jsonify({'error': 'No autorizado'}), 403
    data = request.get_json()
    estatus = data.get('estatus')
    if estatus not in ('pendiente', 'aceptada', 'declinada'):
        return jsonify({'error': 'Estatus inválido'}), 400
    motivo = data.get('motivo', '')
    try:
        db.update_solicitud_status(sid, estatus, motivo)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/admin/actividades', methods=['GET', 'POST'])
def admin_actividades():
    if not session.get('user'):
        return jsonify({'error': 'No autorizado'}), 401

    # POST: create new actividad in Turso
    if request.method == 'POST':
        if session['user'].get('role') not in ('admin', 'worker'):
            return jsonify({'error': 'No autorizado'}), 403
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        required = ('fecha_actividad', 'funcionario', 'tipo_actividad', 'lugar')
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({'error': f'Campos requeridos: {", ".join(missing)}'}), 400
        try:
            act_id = db.create_actividad(
                fecha_actividad=data['fecha_actividad'],
                funcionario=data['funcionario'],
                tipo_actividad=data['tipo_actividad'],
                lugar=data['lugar'],
                funcionarios_count=int(data.get('funcionarios_count', data.get('funcionarios_cant', 0))),
                novedades=data.get('novedades', ''),
                estatus=data.get('estatus', 'En Proceso'),
                solicitud_ref=data.get('solicitud_ref', ''),
            )
            return jsonify({'ok': True, 'id': act_id})
        except Exception as e:
            return jsonify({'error': f'Error al crear actividad: {e}'}), 400

    # GET: Turso actividades only
    rows = []
    for a in db.list_actividades_turso():
        rows.append({
            'id': a['id'],
            'fecha_registro': a['created_at'],
            'fecha_actividad': a['fecha_actividad'],
            'funcionario': a['funcionario'],
            'tipo_actividad': a['tipo_actividad'],
            'lugar': a['lugar'],
            'funcionarios': a['funcionarios_count'],
            'novedades': a['novedades'],
            'estatus': a['estatus'],
            'solicitud_ref': a['solicitud_ref'],
            'source': 'turso',
        })
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

@app.route('/api/admin/actividades/<int:act_id>/status', methods=['PUT'])
def admin_actividad_status(act_id):
    if not session.get('user'):
        return jsonify({'error': 'No autorizado'}), 401
    if session['user'].get('role') not in ('admin', 'worker'):
        return jsonify({'error': 'No autorizado'}), 403
    data = request.get_json()
    estatus = data.get('estatus')
    if estatus not in ('Completado', 'En Proceso'):
        return jsonify({'error': 'Estatus inválido'}), 400
    try:
        db.update_actividad_status(act_id, estatus)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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
    if role not in ('admin', 'worker'):
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
    session.pop('pending_user', None)
    session.pop('_2fa_code', None)
    session.pop('_2fa_expiry', None)
    session.pop('_2fa_email_mask', None)
    return redirect('/')

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', '').lower() in ('1', 'true')
    app.run(host='0.0.0.0', port=5000, debug=debug)

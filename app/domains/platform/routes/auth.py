from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse, urljoin
from app.database import db, login_manager
from app.models.system import User
from app.domains.platform.services.security_service import validate_password_strength
from app.domains.ecommerce.models import WebCustomer
from app.models.master import ERPUser

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

_LOGIN_FAIL_CACHE = {}
_MAX_LOGIN_FAILS = 5
_LOCK_MINUTES = 10
_FAIL_CACHE_TIMEOUT = 600


def _get_fail_info(key):
    try:
        from app.core.extensions import cache
        data = cache.get(f'login_fail:{key}')
        if data is None:
            return [0, None]
        return data
    except Exception:
        return _LOGIN_FAIL_CACHE.get(key, [0, None])


def _set_fail_info(key, info):
    try:
        from app.core.extensions import cache
        cache.set(f'login_fail:{key}', info, timeout=_FAIL_CACHE_TIMEOUT)
    except Exception:
        _LOGIN_FAIL_CACHE[key] = info


def _del_fail_info(key):
    try:
        from app.core.extensions import cache
        cache.delete(f'login_fail:{key}')
    except Exception:
        _LOGIN_FAIL_CACHE.pop(key, None)


def _is_safe_redirect_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@login_manager.user_loader
def load_user(user_id):
    if str(user_id).startswith('web:'):
        from app.domains.ecommerce.models import WebCustomer
        return db.session.get(WebCustomer, int(str(user_id).split(':', 1)[1]))
    return db.session.get(User, int(user_id))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        ip = (request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown').split(',')[0].strip()
        key = f"{ip}:{username.lower()}"
        fail_info = _get_fail_info(key)
        if fail_info[1] and datetime.utcnow() < fail_info[1]:
            left = int((fail_info[1] - datetime.utcnow()).total_seconds() // 60) + 1
            flash(f'Tài khoản tạm khóa đăng nhập. Vui lòng thử lại sau {left} phút.', 'warning')
            return render_template('auth/login.html')
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            _del_fail_info(key)
            user.last_login = datetime.utcnow()
            db.session.commit()
            session.clear()
            session.permanent = True
            login_user(user, remember=bool(remember))
            next_page = request.args.get('next')
            flash(f'Chào mừng {user.full_name}!', 'success')
            return redirect(next_page if _is_safe_redirect_url(next_page) else url_for('dashboard.index'))
        else:
            fail_count = int(fail_info[0]) + 1
            lock_until = None
            if fail_count >= _MAX_LOGIN_FAILS:
                lock_until = datetime.utcnow() + timedelta(minutes=_LOCK_MINUTES)
                fail_count = 0
            _set_fail_info(key, [fail_count, lock_until])
            flash('Tên đăng nhập hoặc mật khẩu không đúng!', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đã đăng xuất thành công.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pw = request.form.get('old_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')
        if not current_user.check_password(old_pw):
            flash('Mật khẩu cũ không đúng!', 'danger')
        elif new_pw != confirm_pw:
            flash('Mật khẩu mới không khớp!', 'danger')
        else:
            ok, msg = validate_password_strength(new_pw)
            if not ok:
                flash(msg, 'warning')
                return render_template('auth/change_password.html')
            current_user.set_password(new_pw)
            db.session.commit()
            flash('Đổi mật khẩu thành công!', 'success')
            return redirect(url_for('dashboard.index'))
    return render_template('auth/change_password.html')


@auth_bp.route('/set-lang/<lang>')
def set_lang(lang):
    allowed = {'vi', 'en'}
    if lang not in allowed:
        lang = 'vi'
    session['lang'] = lang
    resp = redirect(request.referrer or url_for('dashboard.index'))
    resp.set_cookie('lang', lang, max_age=30 * 24 * 3600)
    return resp


@auth_bp.route('/switch-lang/<lang_code>')
def switch_lang(lang_code):
    allowed = {'vi', 'en'}
    if lang_code not in allowed:
        lang_code = 'vi'
    session['lang'] = lang_code
    resp = redirect(request.referrer or url_for('dashboard.index'))
    resp.set_cookie('lang', lang_code, max_age=30 * 24 * 3600)
    return resp

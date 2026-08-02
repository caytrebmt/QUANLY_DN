import os
import subprocess
import datetime
from pathlib import Path
import shutil
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import text
from app.database import db
from app.shared.authz import require_permission
from app.shared.constants import Roles

backup_bp = Blueprint('backup', __name__, url_prefix='')


def _admin_only():
    if current_user.role != Roles.ADMIN:
        flash('Chỉ quản trị viên mới có quyền thực hiện!', 'danger')
        return False
    return True


def _pg_conn_info():
    uri = db.engine.url
    return {
        'user': uri.username or '',
        'password': uri.password or '',
        'host': uri.host or 'localhost',
        'port': uri.port or 5432,
        'database': uri.database or '',
    }


def _resolve_pg_bin(bin_name: str):
    env_map = {
        'pg_dump': 'PG_DUMP_PATH',
        'psql': 'PSQL_PATH',
        'pg_restore': 'PG_RESTORE_PATH',
    }
    env_key = env_map.get(bin_name, '')
    from_env = (os.getenv(env_key, '') or '').strip()
    if from_env and os.path.exists(from_env):
        return from_env

    exe_name = f'{bin_name}.exe' if os.name == 'nt' else bin_name
    pg_bin_dir = (os.getenv('PG_BIN_DIR', '') or '').strip()
    if pg_bin_dir:
        candidate = os.path.join(pg_bin_dir, exe_name)
        if os.path.exists(candidate):
            return candidate

    local_candidates = [
        os.path.join('venv', exe_name),
        os.path.join('venv', 'Scripts', exe_name),
        os.path.join('.venv', exe_name),
        os.path.join('.venv', 'Scripts', exe_name),
    ]
    for c in local_candidates:
        if os.path.exists(c):
            return c

    found = shutil.which(bin_name) or shutil.which(exe_name)
    if found:
        return found

    if os.name == 'nt':
        roots = [
            os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'), 'PostgreSQL'),
            os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), 'PostgreSQL'),
        ]
        for root in roots:
            if not os.path.isdir(root):
                continue
            try:
                versions = sorted(Path(root).iterdir(), reverse=True)
            except Exception:
                versions = []
            for ver_dir in versions:
                candidate = ver_dir / 'bin' / exe_name
                if candidate.exists():
                    return str(candidate)

    raise FileNotFoundError(f'Cannot find PostgreSQL client binary: {bin_name}')


def _cleanup_old_backups(backup_dir: str, keep_days: int = 14):
    cutoff = datetime.datetime.now() - datetime.timedelta(days=max(1, int(keep_days or 14)))
    for p in Path(backup_dir).glob('*'):
        if not p.is_file():
            continue
        try:
            mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
            if mtime < cutoff:
                p.unlink(missing_ok=True)
        except Exception:
            continue


@backup_bp.route('/db/tools')
@login_required
@require_permission('settings', 'view')
def db_tools():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    backup_dir = os.path.join('backups')
    os.makedirs(backup_dir, exist_ok=True)
    files = []
    for p in sorted(Path(backup_dir).glob('*'), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            files.append({
                'name': p.name,
                'size_kb': round(p.stat().st_size / 1024, 1),
                'updated_at': datetime.datetime.fromtimestamp(p.stat().st_mtime),
            })
    return render_template('settings/db_tools.html', backup_files=files)


@backup_bp.route('/db/backup', methods=['POST'])
@login_required
@require_permission('settings', 'edit')
def db_backup():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    info = _pg_conn_info()
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join('backups')
    os.makedirs(backup_dir, exist_ok=True)
    backup_format = (request.form.get('backup_format', 'plain') or 'plain').lower()
    is_custom = backup_format == 'custom'
    ext = 'dump' if is_custom else 'sql'
    file_path = os.path.join(backup_dir, f"{info['database']}_{ts}.{ext}")
    env = os.environ.copy()
    if info['password']:
        env['PGPASSWORD'] = info['password']
    cmd = [
        _resolve_pg_bin('pg_dump'),
        '-h', info['host'],
        '-p', str(info['port']),
        '-U', info['user'],
        '-F', 'c' if is_custom else 'p',
        '-f', file_path,
        info['database'],
    ]
    try:
        subprocess.check_call(cmd, env=env)
        _cleanup_old_backups(backup_dir, int(os.getenv('BACKUP_KEEP_DAYS', '14')))
        flash(f'Backup thành công: {file_path}', 'success')
    except FileNotFoundError:
        flash('Không tìm thấy pg_dump. Hãy đặt PG_DUMP_PATH hoặc PG_BIN_DIR, hoặc thêm PostgreSQL\\bin vào PATH rồi restart app.', 'danger')
    except subprocess.CalledProcessError as e:
        flash(f'Backup lỗi: {e}', 'danger')
    return redirect(url_for('backup.db_tools'))


@backup_bp.route('/db/restore', methods=['POST'])
@login_required
@require_permission('settings', 'delete')
def db_restore():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    upload = request.files.get('sql_file')
    if not upload or not (upload.filename.lower().endswith('.sql') or upload.filename.lower().endswith('.dump')):
        flash('Chọn file .sql hoặc .dump để restore!', 'warning')
        return redirect(url_for('backup.db_tools'))

    info = _pg_conn_info()
    env = os.environ.copy()
    if info['password']:
        env['PGPASSWORD'] = info['password']

    ext = '.dump' if upload.filename.lower().endswith('.dump') else '.sql'
    tmp_path = os.path.join(
        'backups', f"_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    upload.save(tmp_path)

    try:
        if ext == '.dump':
            cmd = [
                _resolve_pg_bin('psql'),
                '-h', info['host'],
                '-p', str(info['port']),
                '-U', info['user'],
                '-d', info['database'],
                '-c', f"DROP SCHEMA public CASCADE; CREATE SCHEMA public;",
            ]
            subprocess.check_call(cmd, env=env)
            cmd_restore = [
                _resolve_pg_bin('pg_restore'),
                '-h', info['host'],
                '-p', str(info['port']),
                '-U', info['user'],
                '-d', info['database'],
                '--clean',
                '--if-exists',
                tmp_path,
            ]
            subprocess.check_call(cmd_restore, env=env)
        else:
            cmd = [
                _resolve_pg_bin('psql'),
                '-h', info['host'],
                '-p', str(info['port']),
                '-U', info['user'],
                '-d', info['database'],
                '-f', tmp_path,
            ]
            subprocess.check_call(cmd, env=env)
        flash('Restore thành công.', 'success')
    except FileNotFoundError as e:
        missing = str(e).replace('Cannot find PostgreSQL client binary: ', '').strip() or 'psql/pg_restore'
        flash(f'Không tìm thấy {missing}. Hãy đặt *_PATH hoặc PG_BIN_DIR, hoặc thêm PostgreSQL\\bin vào PATH rồi restart app.', 'danger')
    except subprocess.CalledProcessError as e:
        flash(f'Restore lỗi: {e}', 'danger')
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    return redirect(url_for('backup.db_tools'))


@backup_bp.route('/db/verify', methods=['POST'])
@login_required
@require_permission('settings', 'edit')
def db_verify():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    try:
        db.session.execute(text('SELECT 1'))
        checks = {
            'users': db.session.execute(text('SELECT COUNT(*) FROM users')).scalar() or 0,
            'products': db.session.execute(text('SELECT COUNT(*) FROM products')).scalar() or 0,
            'inventory': db.session.execute(text('SELECT COUNT(*) FROM inventory')).scalar() or 0,
            'journal_entries': db.session.execute(text('SELECT COUNT(*) FROM journal_entries')).scalar() or 0,
        }
        flash(
            'DB verify OK | ' + ' | '.join([f"{k}:{v}" for k, v in checks.items()]),
            'success'
        )
    except Exception as e:
        flash(f'DB verify lỗi: {e}', 'danger')
    return redirect(url_for('backup.db_tools'))

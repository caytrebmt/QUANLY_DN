#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║          ERPmini - Setup Wizard v1.0                         ║
║             Setup For Windows + VSCode                       ║
╚══════════════════════════════════════════════════════════════╝

    python setup_wizard.py
"""

import os
import sys
import subprocess
import shutil
import platform
import re
import json
import time
import socket
from pathlib import Path
from datetime import datetime

# ── Màu sắc console ────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    BG_BLUE  = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_RED   = "\033[41m"

def _enable_win_colors():
    """Bật ANSI colors trên Windows"""
    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

_enable_win_colors()

IS_WINDOWS = platform.system() == "Windows"
BASE_DIR   = Path(__file__).parent.resolve()

# ── Helpers in/out ─────────────────────────────────────────────
def c(text, color=C.RESET):
    return f"{color}{text}{C.RESET}"

def header(title: str):
    w = 62
    print()
    print(c("─" * w, C.CYAN))
    print(c(f"  {title}", C.BOLD + C.WHITE))
    print(c("─" * w, C.CYAN))

def ok(msg):    print(c(f"  ✓  {msg}", C.GREEN))
def info(msg):  print(c(f"  ℹ  {msg}", C.CYAN))
def warn(msg):  print(c(f"  ⚠  {msg}", C.YELLOW))
def fail(msg):  print(c(f"  ✗  {msg}", C.RED))
def step(n, msg): print(c(f"\n  [{n}]  {msg}", C.BOLD + C.BLUE))

def ask(prompt, default="", required=False, secret=False):
    """Hỏi người dùng, có giá trị mặc định"""
    if default:
        display = f"{c(prompt, C.WHITE)} {c(f'[{default}]', C.YELLOW)}: "
    else:
        display = f"{c(prompt, C.WHITE)}: "
    while True:
        if secret:
            import getpass
            val = getpass.getpass(display)
        else:
            val = input(display).strip()
        if not val and default:
            return default
        if val or not required:
            return val
        warn("Giá trị này là bắt buộc, vui lòng nhập!")

def ask_yes(prompt, default=True) -> bool:
    yn = "Y/n" if default else "y/N"
    val = input(f"  {c(prompt, C.WHITE)} [{c(yn, C.YELLOW)}]: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes", "có", "co", "1")

def run_cmd(cmd, cwd=None, capture=True, env=None):
    """Chạy lệnh shell, trả về (returncode, stdout, stderr)"""
    if isinstance(cmd, str):
        cmd_list = cmd
        shell = True
    else:
        cmd_list = cmd
        shell = False
    result = subprocess.run(
        cmd_list, cwd=str(cwd or BASE_DIR),
        capture_output=capture, text=True, shell=shell,
        env=env or os.environ.copy()
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def pip_path(venv_dir: Path):
    if IS_WINDOWS:
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"

def python_path(venv_dir: Path):
    if IS_WINDOWS:
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"

def check_port(host, port, timeout=2) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except Exception:
        return False

# ═══════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════
def show_banner():
    os.system("cls" if IS_WINDOWS else "clear")
    print(c(r"""
  ███████╗██████╗ ██████╗ ███╗   ███╗██╗███╗   ██╗██╗
  ██╔════╝██╔══██╗██╔══██╗████╗ ████║██║████╗  ██║██║
  █████╗  ██████╔╝██████╔╝██╔████╔██║██║██╔██╗ ██║██║
  ██╔══╝  ██╔══██╗██╔═══╝ ██║╚██╔╝██║██║██║╚██╗██║██║
  ███████╗██║  ██║██║     ██║ ╚═╝ ██║██║██║ ╚████║██║
  ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝
""", C.CYAN))
    print(c("  Setup Wizard - Trợ lý cài đặt tự động", C.BOLD + C.WHITE))
    print(c("  Hệ thống ERP quản lý doanh nghiệp Việt Nam", C.YELLOW))
    print(c(f"  Thư mục dự án: {BASE_DIR}", C.CYAN))
    print()

# ═══════════════════════════════════════════════════════════════
# STEP 1: Kiểm tra Python
# ═══════════════════════════════════════════════════════════════
def check_python():
    header("Bước 1/8 — Kiểm tra Python")
    ver = sys.version_info
    ver_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    if ver.major < 3 or (ver.major == 3 and ver.minor < 9):
        fail(f"Python {ver_str} quá cũ. Cần Python 3.9+")
        fail("Tải Python tại: https://www.python.org/downloads/")
        sys.exit(1)
    ok(f"Python {ver_str} ✓")
    ok(f"Đường dẫn: {sys.executable}")
    return True

# ═══════════════════════════════════════════════════════════════
# STEP 2: Kiểm tra PostgreSQL
# ═══════════════════════════════════════════════════════════════
def check_postgresql():
    header("Bước 2/8 — Kiểm tra PostgreSQL")

    # Tìm psql
    psql = shutil.which("psql")
    if psql:
        rc, out, _ = run_cmd("psql --version")
        ok(f"PostgreSQL tìm thấy: {out}")
        ok(f"psql path: {psql}")
    else:
        warn("Không tìm thấy lệnh 'psql' trong PATH")
        info("Kiểm tra PostgreSQL có đang chạy trên port 5432...")
        if check_port("localhost", 5432):
            ok("PostgreSQL đang chạy trên port 5432")
        else:
            fail("PostgreSQL KHÔNG tìm thấy!")
            print()
            print(c("  Vui lòng cài đặt PostgreSQL:", C.YELLOW))
            print(c("  → https://www.enterprisedb.com/downloads/postgres-postgresql-downloads", C.CYAN))
            print(c("  → Hoặc dùng: winget install PostgreSQL.PostgreSQL", C.CYAN))
            if IS_WINDOWS:
                print(c("  → Sau khi cài, thêm PostgreSQL\\bin vào PATH", C.CYAN))
            print()
            if not ask_yes("Bạn vẫn muốn tiếp tục? (PostgreSQL cần được cài trước)", default=False):
                sys.exit(1)

    return psql

# ═══════════════════════════════════════════════════════════════
# STEP 3: Cấu hình kết nối Database
# ═══════════════════════════════════════════════════════════════
def configure_database():
    header("Bước 3/8 — Cấu hình cơ sở dữ liệu PostgreSQL")

    info("Nhập thông tin kết nối PostgreSQL:")
    print()

    db_host = ask("Host PostgreSQL", "localhost")
    db_port = ask("Port PostgreSQL", "5432")
    db_name = ask("Tên database", "erpmini")
    db_user = ask("Username PostgreSQL", "postgres")
    db_pass = ask("Password PostgreSQL", secret=True, required=True)

    db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    # Test kết nối
    info("Kiểm tra kết nối...")
    test_sql = f"SELECT 1;"
    psql_cmd = f'psql "postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/postgres" -c "{test_sql}" -t -q'
    rc, out, err = run_cmd(psql_cmd)

    if rc != 0:
        warn(f"Không thể kết nối: {err[:100]}")
        warn("Tiếp tục với thông tin đã nhập...")
    else:
        ok("Kết nối PostgreSQL thành công!")

    # Tạo database nếu chưa có
    info(f"Kiểm tra database '{db_name}'...")
    check_db_cmd = f'psql "postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/postgres" -c "SELECT 1 FROM pg_database WHERE datname=\'{db_name}\';" -t -q'
    rc, out, _ = run_cmd(check_db_cmd)

    if "1" not in out:
        info(f"Database '{db_name}' chưa tồn tại, đang tạo...")
        create_cmd = f'psql "postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/postgres" -c "CREATE DATABASE {db_name} ENCODING=\'UTF8\';"'
        rc, out, err = run_cmd(create_cmd)
        if rc == 0:
            ok(f"Đã tạo database '{db_name}'")
        else:
            warn(f"Lỗi tạo database: {err[:120]}")
            warn("Bạn có thể tạo thủ công sau: CREATE DATABASE erpmini;")
    else:
        ok(f"Database '{db_name}' đã tồn tại")

    return {
        "host": db_host, "port": db_port,
        "name": db_name, "user": db_user,
        "pass": db_pass, "url": db_url
    }

# ═══════════════════════════════════════════════════════════════
# STEP 4: Cấu hình công ty
# ═══════════════════════════════════════════════════════════════
def configure_company():
    header("Bước 4/8 — Thông tin công ty")

    info("Nhập thông tin công ty của bạn (dùng in phiếu, báo cáo):")
    print()

    company = {
        "name":    ask("Tên công ty",      "Công ty TNHH ERPmini"),
        "address": ask("Địa chỉ",          "123 Đường ABC, TP.HCM"),
        "phone":   ask("Điện thoại",       "028-1234-5678"),
        "tax":     ask("Mã số thuế",       "0312345678"),
        "email":   ask("Email",            "info@erpmini.com"),
        "port":    ask("Cổng chạy ứng dụng (App Port)", "5000"),
    }

    # Secret key
    import secrets
    company["secret_key"] = secrets.token_hex(32)
    ok("Đã tạo SECRET_KEY ngẫu nhiên an toàn")

    return company

# ═══════════════════════════════════════════════════════════════
# STEP 5: Tạo .env
# ═══════════════════════════════════════════════════════════════
def create_env_file(db_cfg, company_cfg):
    header("Bước 5/8 — Tạo file cấu hình .env")

    env_content = f"""# ERPmini Configuration
# Được tạo tự động bởi setup_wizard.py vào {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FLASK_APP=run.py
FLASK_ENV=development

# Bảo mật (đừng chia sẻ key này!)
SECRET_KEY={company_cfg['secret_key']}

# Kết nối PostgreSQL
DATABASE_URL={db_cfg['url']}

# Thông tin công ty
COMPANY_NAME={company_cfg['name']}
COMPANY_ADDRESS={company_cfg['address']}
COMPANY_PHONE={company_cfg['phone']}
COMPANY_TAX_CODE={company_cfg['tax']}
COMPANY_EMAIL={company_cfg['email']}

# App
PORT={company_cfg['port']}
"""

    env_path = BASE_DIR / ".env"

    if env_path.exists():
        backup = BASE_DIR / f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(env_path, backup)
        warn(f"File .env cũ đã được backup: {backup.name}")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    ok(f"Đã tạo file: {env_path}")
    return env_path

# ═══════════════════════════════════════════════════════════════
# STEP 6: Tạo Virtual Environment + cài thư viện
# ═══════════════════════════════════════════════════════════════
def setup_venv():
    header("Bước 6/8 — Tạo môi trường ảo Python (venv)")

    venv_dir = BASE_DIR / "venv"

    if venv_dir.exists():
        if ask_yes("Thư mục 'venv' đã tồn tại. Dùng lại?", default=True):
            ok("Dùng venv hiện có")
        else:
            info("Đang xóa venv cũ...")
            shutil.rmtree(venv_dir)
            info("Đang tạo venv mới...")
            rc, _, err = run_cmd([sys.executable, "-m", "venv", str(venv_dir)], capture=True)
            if rc != 0:
                fail(f"Lỗi tạo venv: {err}")
                sys.exit(1)
            ok("Đã tạo virtual environment")
    else:
        info("Đang tạo virtual environment...")
        rc, _, err = run_cmd([sys.executable, "-m", "venv", str(venv_dir)], capture=True)
        if rc != 0:
            fail(f"Lỗi tạo venv: {err}")
            sys.exit(1)
        ok("Đã tạo virtual environment")

    pip = pip_path(venv_dir)
    py  = python_path(venv_dir)

    # Upgrade pip
    info("Nâng cấp pip...")
    rc, out, err = run_cmd([str(py), "-m", "pip", "install", "--upgrade", "pip", "-q"], capture=True)
    if rc == 0:
        ok("pip đã được nâng cấp")
    else:
        warn("Không thể nâng cấp pip, tiếp tục...")

    # Cài requirements
    req_file = BASE_DIR / "requirements.txt"
    if not req_file.exists():
        fail("Không tìm thấy requirements.txt!")
        sys.exit(1)

    info("Đang cài đặt thư viện Python (có thể mất 2-5 phút)...")
    print(c("  Vui lòng chờ...", C.YELLOW))
    print()

    packages = [line.strip() for line in req_file.read_text().splitlines()
                if line.strip() and not line.startswith("#")]

    total = len(packages)
    failed_pkgs = []

    for i, pkg in enumerate(packages, 1):
        pkg_name = re.split(r'[>=<!]', pkg)[0].strip()
        print(f"  [{i:2d}/{total}] Đang cài: {c(pkg_name, C.CYAN)}...", end="\r")
        rc, out, err = run_cmd(
            [str(pip), "install", pkg, "-q", "--disable-pip-version-check"],
            capture=True
        )
        if rc == 0:
            print(f"  [{i:2d}/{total}] {c('✓', C.GREEN)} {pkg_name:<40}")
        else:
            print(f"  [{i:2d}/{total}] {c('✗', C.RED)} {pkg_name:<40} (sẽ thử lại)")
            failed_pkgs.append(pkg)

    # Thử lại các gói lỗi
    if failed_pkgs:
        print()
        warn(f"Thử lại {len(failed_pkgs)} gói bị lỗi...")
        still_failed = []
        for pkg in failed_pkgs:
            pkg_name = re.split(r'[>=<!]', pkg)[0].strip()
            rc, _, err = run_cmd([str(pip), "install", pkg, "--no-cache-dir", "-q"], capture=True)
            if rc == 0:
                ok(f"Đã cài: {pkg_name}")
            else:
                fail(f"KHÔNG thể cài: {pkg_name} — {err[:80]}")
                still_failed.append(pkg)

        if still_failed:
            warn("Một số gói không thể cài tự động:")
            for p in still_failed:
                print(f"      {c(p, C.RED)}")
            warn("Bạn có thể cài thủ công sau: pip install <tên_gói>")

    print()
    ok(f"Đã cài xong {total - len(failed_pkgs)}/{total} thư viện")
    return venv_dir, py

# ═══════════════════════════════════════════════════════════════
# STEP 7: Khởi tạo Database
# ═══════════════════════════════════════════════════════════════
def init_database(py_path: Path):
    header("Bước 7/8 — Khởi tạo cơ sở dữ liệu & dữ liệu mẫu")

    init_script = BASE_DIR / "init_db.py"
    if not init_script.exists():
        fail("Không tìm thấy init_db.py!")
        sys.exit(1)

    info("Đang tạo bảng dữ liệu và nhập dữ liệu mẫu...")
    info("(Bao gồm: tài khoản, menu, thông báo, kho, hàng hóa, KH, NCC, ...)")
    print()

    # Chạy init_db.py với venv python
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR)

    process = subprocess.Popen(
        [str(py_path), str(init_script)],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env
    )

    lines_printed = 0
    for line in process.stdout:
        line = line.rstrip()
        if line:
            if "✅" in line or "OK" in line.upper():
                print(c(f"  {line}", C.GREEN))
            elif "⚠️" in line or "WARNING" in line.upper():
                print(c(f"  {line}", C.YELLOW))
            elif "ERROR" in line.upper() or "✗" in line:
                print(c(f"  {line}", C.RED))
            else:
                print(f"  {line}")
            lines_printed += 1

    process.wait()

    if process.returncode == 0:
        print()
        ok("Khởi tạo database hoàn tất!")
    else:
        print()
        fail(f"init_db.py kết thúc với mã lỗi: {process.returncode}")
        warn("Bạn có thể thử chạy thủ công: python init_db.py")

    return process.returncode == 0

# ═══════════════════════════════════════════════════════════════
# STEP 8: Tạo scripts khởi động
# ═══════════════════════════════════════════════════════════════
def create_launchers(venv_dir: Path, port: str):
    header("Bước 8/8 — Tạo script khởi động")

    # Windows .bat
    bat_content = f"""@echo off
chcp 65001 >nul
title ERPmini Server
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       ERPmini - Đang khởi động...           ║
echo  ╚══════════════════════════════════════════════╝
echo.
cd /d "%~dp0"
call venv\\Scripts\\activate.bat
echo  [INFO] Ứng dụng sẽ chạy tại: http://localhost:{port}
echo  [INFO] Nhấn Ctrl+C để dừng server
echo.
python run.py
pause
"""
    bat_path = BASE_DIR / "start_erpmini.bat"
    bat_path.write_text(bat_content, encoding="utf-8")
    ok(f"Đã tạo: start_erpmini.bat")

    # Windows .bat - chỉ mở browser
    open_bat = f"""@echo off
start http://localhost:{port}
"""
    (BASE_DIR / "open_browser.bat").write_text(open_bat, encoding="utf-8")
    ok(f"Đã tạo: open_browser.bat")

    # Linux/Mac .sh
    sh_content = f"""#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo ""
echo "  ERPmini đang khởi động..."
echo "  Truy cập: http://localhost:{port}"
echo "  Nhấn Ctrl+C để dừng"
echo ""
python run.py
"""
    sh_path = BASE_DIR / "start_erpmini.sh"
    sh_path.write_text(sh_content, encoding="utf-8")
    try:
        os.chmod(sh_path, 0o755)
    except Exception:
        pass
    ok(f"Đã tạo: start_erpmini.sh")

    # VSCode launch.json
    vscode_dir = BASE_DIR / ".vscode"
    vscode_dir.mkdir(exist_ok=True)

    launch_json = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "ERPmini Flask Server",
                "type": "debugpy",
                "request": "launch",
                "program": str(BASE_DIR / "run.py"),
                "cwd": str(BASE_DIR),
                "env": {
                    "FLASK_ENV": "production",
                    "FLASK_DEBUG": "1"
                },
                "jinja": True,
                "console": "integratedTerminal",
                "pythonPath": str(python_path(venv_dir))
            }
        ]
    }
    launch_path = vscode_dir / "launch.json"
    with open(launch_path, "w", encoding="utf-8") as f:
        json.dump(launch_json, f, indent=2, ensure_ascii=False)
    ok(f"Đã tạo: .vscode/launch.json (F5 để debug trong VSCode)")

    # settings.json cho VSCode
    settings_json = {
        "python.defaultInterpreterPath": str(python_path(venv_dir)),
        "python.terminal.activateEnvironment": True,
        "editor.formatOnSave": True,
        "files.encoding": "utf8",
        "[python]": {
            "editor.tabSize": 4
        }
    }
    settings_path = vscode_dir / "settings.json"
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings_json, f, indent=2, ensure_ascii=False)
    ok(f"Đã tạo: .vscode/settings.json")

    return bat_path

# ═══════════════════════════════════════════════════════════════
# HOÀN TẤT - Tóm tắt
# ═══════════════════════════════════════════════════════════════
def show_summary(db_cfg, company_cfg, venv_dir: Path):
    port = company_cfg["port"]
    print()
    print(c("═" * 62, C.GREEN))
    print(c("  🎉  CÀI ĐẶT HOÀN TẤT! ERPmini đã sẵn sàng.", C.BOLD + C.GREEN))
    print(c("═" * 62, C.GREEN))
    print()
    print(c("  📋  THÔNG TIN HỆ THỐNG", C.BOLD + C.WHITE))
    print(c("  ─" * 30, C.CYAN))
    print(f"  {'URL ứng dụng:':<24} {c(f'http://localhost:{port}', C.CYAN + C.BOLD)}")
    print(f"  {'Tài khoản Admin:':<24} {c('admin', C.YELLOW)} / {c('(xem console)', C.YELLOW)}")
    print(f"  {'Tài khoản Kế toán:':<24} {c('ketoan', C.YELLOW)} / {c('(xem console)', C.YELLOW)}")
    print(f"  {'Database:':<24} {c(db_cfg['name'], C.CYAN)} @ {db_cfg['host']}:{db_cfg['port']}")
    print(f"  {'Công ty:':<24} {company_cfg['name']}")
    print(f"  {'Thư mục dự án:':<24} {BASE_DIR}")
    print()
    print(c("  🚀  CÁCH KHỞI ĐỘNG", C.BOLD + C.WHITE))
    print(c("  ─" * 30, C.CYAN))
    if IS_WINDOWS:
        print(f"  {c('→ Double-click:', C.GREEN)} {c('start_erpmini.bat', C.YELLOW)}")
        print(f"  {c('→ VSCode F5:', C.GREEN)}      {c('Mở VSCode → F5 để debug', C.YELLOW)}")
        print(f"  {c('→ Terminal:', C.GREEN)}        venv\\Scripts\\activate → python run.py")
    else:
        print(f"  {c('→ Terminal:', C.GREEN)}  ./start_erpmini.sh")
        print(f"  {c('→ Hoặc:', C.GREEN)}     source venv/bin/activate && python run.py")
    print()
    print(c("  📁  FILES ĐÃ TẠO", C.BOLD + C.WHITE))
    print(c("  ─" * 30, C.CYAN))
    files_created = [
        (".env",                "Cấu hình database & company"),
        ("start_erpmini.bat",   "Script khởi động Windows"),
        ("start_erpmini.sh",    "Script khởi động Linux/Mac"),
        ("open_browser.bat",    "Mở trình duyệt nhanh"),
        (".vscode/launch.json", "Cấu hình debug VSCode"),
        (".vscode/settings.json","Cài đặt VSCode"),
        ("venv/",               "Python virtual environment"),
    ]
    for fname, desc in files_created:
        fpath = BASE_DIR / fname
        exists = fpath.exists() or (BASE_DIR / ".vscode").exists() and "vscode" in fname
        icon = c("✓", C.GREEN) if exists else c("○", C.YELLOW)
        print(f"  {icon}  {fname:<28} {c(desc, C.CYAN)}")
    print()
    print(c("  ⚠️   LƯU Ý BẢO MẬT", C.BOLD + C.YELLOW))
    print(c("  ─" * 30, C.CYAN))
    print(c("  • Đổi mật khẩu admin sau lần đăng nhập đầu tiên", C.YELLOW))
    print(c("  • Không chia sẻ file .env (chứa password DB)", C.YELLOW))
    print(c("  • Thêm .env vào .gitignore nếu dùng Git", C.YELLOW))
    print()

    # Hỏi có muốn khởi động ngay không
    if ask_yes("\n  Khởi động ERPmini ngay bây giờ?", default=True):
        launch_app(company_cfg["port"])

def launch_app(port: str):
    """Khởi động ứng dụng Flask"""
    print()
    info(f"Đang khởi động ERPmini trên port {port}...")
    time.sleep(1)

    # Mở browser trước
    def open_browser():
        time.sleep(3)
        try:
            import webbrowser
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass

    import threading
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    # Khởi động Flask
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR)
    venv_py = BASE_DIR / "venv" / ("Scripts" if IS_WINDOWS else "bin") / ("python.exe" if IS_WINDOWS else "python")

    py_exec = str(venv_py) if venv_py.exists() else sys.executable

    print(c(f"\n  → Truy cập: http://localhost:{port}", C.BOLD + C.CYAN))
    print(c("  → Nhấn Ctrl+C để dừng server\n", C.YELLOW))

    try:
        subprocess.run(
            [py_exec, str(BASE_DIR / "run.py")],
            cwd=str(BASE_DIR),
            env=env
        )
    except KeyboardInterrupt:
        print()
        info("Đã dừng server ERPmini.")

# ═══════════════════════════════════════════════════════════════
# KIỂM TRA CẤU HÌNH HIỆN TẠI
# ═══════════════════════════════════════════════════════════════
def check_existing_install():
    """Phát hiện cài đặt cũ và hỏi xem có muốn cài lại không"""
    env_file = BASE_DIR / ".env"
    venv_dir = BASE_DIR / "venv"

    if env_file.exists() or venv_dir.exists():
        print()
        warn("Phát hiện cài đặt cũ:")
        if env_file.exists():
            print(c("  • File .env đã tồn tại", C.YELLOW))
        if venv_dir.exists():
            print(c("  • Thư mục venv đã tồn tại", C.YELLOW))
        print()

        choice = input(c(
            "  Chọn chế độ:\n"
            "  [1] Cài đặt lại hoàn toàn (xóa cũ)\n"
            "  [2] Chỉ cập nhật thư viện và database\n"
            "  [3] Chỉ chạy ứng dụng (bỏ qua cài đặt)\n"
            "  [4] Thoát\n"
            "  Lựa chọn [1/2/3/4]: ", C.WHITE
        )).strip()

        if choice == "1":
            if venv_dir.exists():
                info("Đang xóa venv cũ...")
                shutil.rmtree(venv_dir)
            return "fresh"
        elif choice == "2":
            return "update"
        elif choice == "3":
            return "run_only"
        else:
            print(c("\n  Tạm biệt!", C.CYAN))
            sys.exit(0)

    return "fresh"

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    show_banner()

    print(c("  Wizard này sẽ:", C.WHITE))
    print(c("  ① Kiểm tra Python & PostgreSQL", C.CYAN))
    print(c("  ② Cấu hình kết nối database", C.CYAN))
    print(c("  ③ Nhập thông tin công ty của bạn", C.CYAN))
    print(c("  ④ Tạo virtual environment & cài thư viện", C.CYAN))
    print(c("  ⑤ Tạo bảng DB & nhập dữ liệu mẫu", C.CYAN))
    print(c("  ⑥ Tạo script khởi động & cấu hình VSCode", C.CYAN))
    print()

    if not ask_yes("Bắt đầu cài đặt?", default=True):
        print(c("\n  Đã hủy. Chạy lại khi bạn sẵn sàng.\n", C.YELLOW))
        sys.exit(0)

    # Phát hiện cài đặt cũ
    mode = check_existing_install()

    if mode == "run_only":
        env_file = BASE_DIR / ".env"
        port = "5000"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("PORT="):
                    port = line.split("=", 1)[1].strip()
        launch_app(port)
        return

    # Cài đặt đầy đủ hoặc update
    check_python()
    check_postgresql()

    if mode == "fresh":
        db_cfg = configure_database()
        company_cfg = configure_company()
        env_path = create_env_file(db_cfg, company_cfg)
    else:
        # Update: đọc .env cũ
        info("Đọc cấu hình từ .env hiện tại...")
        env_data = {}
        env_file = BASE_DIR / ".env"
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env_data[k.strip()] = v.strip()

        db_url = env_data.get("DATABASE_URL", "")
        m = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if m:
            db_cfg = {"user":m.group(1),"pass":m.group(2),"host":m.group(3),
                      "port":m.group(4),"name":m.group(5),"url":db_url}
            ok(f"Database: {db_cfg['name']} @ {db_cfg['host']}")
        else:
            db_cfg = configure_database()
            create_env_file(db_cfg, {"name":"ERPmini","address":"","phone":"",
                                      "tax":"","email":"","port":"5000",
                                      "secret_key":"change-me"})

        company_cfg = {
            "name": env_data.get("COMPANY_NAME", "ERPmini"),
            "address": env_data.get("COMPANY_ADDRESS", ""),
            "phone": env_data.get("COMPANY_PHONE", ""),
            "tax": env_data.get("COMPANY_TAX_CODE", ""),
            "email": env_data.get("COMPANY_EMAIL", ""),
            "port": env_data.get("PORT", "5000"),
        }

    venv_dir, py_exec = setup_venv()
    init_database(py_exec)
    create_launchers(venv_dir, company_cfg["port"])
    show_summary(db_cfg, company_cfg, venv_dir)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\n\n  Đã hủy cài đặt.\n", C.YELLOW))
        sys.exit(0)
    except Exception as e:
        print()
        fail(f"Lỗi không mong đợi: {e}")
        import traceback
        traceback.print_exc()
        print()
        warn("Vui lòng chụp màn hình lỗi và liên hệ hỗ trợ.")
        input("  Nhấn Enter để thoát...")
        sys.exit(1)

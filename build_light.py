#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║     ERP-VIET — Lightweight Source-Code Package Builder       ║
║                                                              ║
║  Đóng gói source code sạch (KHÔNG cần PyInstaller)          ║
║  Kết quả: ZIP ~10-15 MB, chạy nhanh hơn PyInstaller         ║
║                                                              ║
║  Máy đích chỉ cần:                                           ║
║    • Python 3.9+  (python.org, miễn phí)                     ║
║    • PostgreSQL 13+                                          ║
║  Sau đó chạy: INSTALL.bat → tự cài đặt hoàn toàn            ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_NAME = "ERP-VIET-Light"
DIST_DIR = BASE_DIR / "dist"
OUTPUT_DIR = DIST_DIR / OUTPUT_NAME

# ── Danh sách file/folder cần đóng gói ───────────────────────
INCLUDE_FILES = [
    # Core Python source
    'run.py',
    'wsgi.py',
    'init_db.py',
    'wait_for_db.py',
    'setup_wizard.py',
    'launcher.py',
    'gunicorn.conf.py',
    'migrate_add_vat_grouped.py',

    # Config
    'requirements.txt',
    '.env.example',
    'babel.cfg',

    # Assets
    'icon.ico',
    'splash.png',

    # Docs
    'README.md',
    'INSTALL.md',
    'HUONG_DAN_CAI_DAT.md',
]

INCLUDE_DIRS = [
    'app',
    'config',
    'translations',
]

# ── Patterns cần loại bỏ ──────────────────────────────────────
EXCLUDE_PATTERNS = {
    '__pycache__',
    '.pyc',
    '.pyo',
    '.pyd',
    '.git',
    '.idea',
    '.vscode',
    'node_modules',
    '.DS_Store',
    'Thumbs.db',
    'desktop.ini',
}

EXCLUDE_DIRS = {
    '__pycache__',
    '.git',
    '.idea',
    '.vscode',
    'node_modules',
}


class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"

def ok(msg):   print(f"{C.GREEN}  ✓  {msg}{C.RESET}")
def info(msg): print(f"{C.CYAN}  ℹ  {msg}{C.RESET}")
def warn(msg): print(f"{C.YELLOW}  ⚠  {msg}{C.RESET}")
def fail(msg): print(f"{C.RED}  ✗  {msg}{C.RESET}")


def should_exclude(path: Path) -> bool:
    """Kiểm tra file/folder có cần loại bỏ không."""
    name = path.name
    if name in EXCLUDE_DIRS:
        return True
    for pattern in EXCLUDE_PATTERNS:
        if name == pattern or name.endswith(pattern):
            return True
    return False


def clean_output():
    """Xóa output cũ."""
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ok("Đã dọn thư mục output")


def copy_files():
    """Copy source files."""
    count = 0

    # Copy individual files
    for fname in INCLUDE_FILES:
        src = BASE_DIR / fname
        if src.exists():
            dst = OUTPUT_DIR / fname
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            count += 1

    # Copy directories
    for dirname in INCLUDE_DIRS:
        src_dir = BASE_DIR / dirname
        if not src_dir.exists():
            warn(f"Thư mục {dirname}/ không tìm thấy, bỏ qua")
            continue

        for root, dirs, files in os.walk(src_dir):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for f in files:
                src_file = Path(root) / f
                if should_exclude(src_file):
                    continue
                rel_path = src_file.relative_to(BASE_DIR)
                dst_file = OUTPUT_DIR / rel_path
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                count += 1

    ok(f"Đã copy {count} files")
    return count


def create_install_bat():
    """Tạo file INSTALL.bat tự động cài đặt."""
    content = r"""@echo off
chcp 65001 >nul
title ERP-VIET - Cai dat tu dong
color 0A

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║     ERP-VIET - Cai dat tu dong                  ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ── Kiem tra Python ──────────────────────────────────
echo  [1/4] Kiem tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [LOI] Python chua duoc cai dat!
    echo.
    echo  Vui long cai Python 3.9+ tai:
    echo  https://www.python.org/downloads/
    echo.
    echo  LUU Y: Tick chon "Add Python to PATH" khi cai!
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] Python %PYVER%

:: ── Tao Virtual Environment ──────────────────────────
echo.
echo  [2/4] Tao moi truong ao (venv)...
if not exist "venv\Scripts\python.exe" (
    python -m venv venv
    echo  [OK] Da tao venv
) else (
    echo  [OK] venv da ton tai, su dung lai
)

:: ── Cai thu vien ─────────────────────────────────────
echo.
echo  [3/4] Cai dat thu vien (co the mat 2-5 phut)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q 2>nul
pip install -r requirements.txt -q --disable-pip-version-check
if errorlevel 1 (
    echo  [CANH BAO] Mot so thu vien co the chua cai duoc.
    echo  Thu lai: pip install -r requirements.txt
) else (
    echo  [OK] Da cai xong thu vien
)

:: ── Chay Setup Wizard ────────────────────────────────
echo.
echo  [4/4] Cau hinh co so du lieu...
echo.
python setup_wizard.py

echo.
echo  ══════════════════════════════════════════════════
echo   CAI DAT HOAN TAT!
echo  ══════════════════════════════════════════════════
echo.
echo   Cach khoi dong:
echo     1. Double-click  RUN.bat
echo     2. Hoac:  venv\Scripts\activate  ^&  python run.py
echo.
echo   Tai khoan: Xem mat khau trong console khi chay INSTALL.bat
echo   URL:       http://localhost:5000
echo.
pause
"""
    (OUTPUT_DIR / "INSTALL.bat").write_text(content, encoding="utf-8")
    ok("Đã tạo INSTALL.bat")


def create_run_bat():
    """Tạo file RUN.bat khởi động nhanh."""
    content = r"""@echo off
chcp 65001 >nul
title ERP-VIET Server
cd /d "%~dp0"

:: Kiem tra venv
if not exist "venv\Scripts\python.exe" (
    echo.
    echo  [LOI] Chua cai dat! Chay INSTALL.bat truoc.
    echo.
    pause
    exit /b 1
)

:: Khoi dong
call venv\Scripts\activate.bat
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║       ERP-VIET dang khoi dong...                ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  [INFO] URL:  http://localhost:5000
echo  [INFO] Nhan Ctrl+C de dung server
echo.

:: Mo browser sau 3 giay
start /b cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:5000"

:: Chay server
python run.py
pause
"""
    (OUTPUT_DIR / "RUN.bat").write_text(content, encoding="utf-8")
    ok("Đã tạo RUN.bat")


def create_run_launcher_bat():
    """Tạo file RUN_GUI.bat chạy launcher GUI (system tray)."""
    content = r"""@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo  [LOI] Chua cai dat! Chay INSTALL.bat truoc.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
start /b pythonw launcher.py
"""
    (OUTPUT_DIR / "RUN_GUI.bat").write_text(content, encoding="utf-8")
    ok("Đã tạo RUN_GUI.bat (chạy với system tray)")


def create_readme():
    """Tạo hướng dẫn nhanh."""
    content = f"""╔══════════════════════════════════════════════════════════════╗
║              ERP-VIET — Gói cài đặt nhẹ                      ║
║              Build: {datetime.now().strftime('%Y-%m-%d %H:%M')}                          ║
╚══════════════════════════════════════════════════════════════╝


 YÊU CẦU:
 ────────
 • Python 3.9+    → https://www.python.org/downloads/
   (Khi cài, TICK chọn "Add Python to PATH")
 • PostgreSQL 13+ → https://www.enterprisedb.com/downloads/


 CÀI ĐẶT (chỉ cần lần đầu):
 ────────────────────────────
 1. Giải nén thư mục ERP-VIET-Light
 2. Double-click  INSTALL.bat
    → Tự tạo venv, cài thư viện, cấu hình DB


 KHỞI ĐỘNG:
 ──────────
 • Cách 1: Double-click  RUN.bat      (console mode)
 • Cách 2: Double-click  RUN_GUI.bat  (system tray mode)
 • Truy cập: http://localhost:5000


  TÀI KHOẢN:
  ──────────
  • Xem mat khau trong console khi chay INSTALL.bat
  • Khoi dong: Double-click RUN.bat
"""
    (OUTPUT_DIR / "HUONG_DAN.txt").write_text(content, encoding="utf-8")
    ok("Đã tạo HUONG_DAN.txt")


def create_zip():
    """Nén thành ZIP."""
    zip_name = f"ERP-VIET-Light_{datetime.now().strftime('%Y%m%d')}.zip"
    zip_path = DIST_DIR / zip_name

    if zip_path.exists():
        zip_path.unlink()

    info(f"Đang nén thành {zip_name}...")

    file_count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                full_path = os.path.join(root, f)
                arc_name = os.path.join(OUTPUT_NAME, os.path.relpath(full_path, OUTPUT_DIR))
                zf.write(full_path, arc_name)
                file_count += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    ok(f"Đã tạo {zip_name} ({size_mb:.1f} MB, {file_count} files)")
    return zip_path, size_mb, file_count


def show_summary(zip_path, size_mb, file_count):
    """Tóm tắt kết quả."""
    print()
    print(f"{C.GREEN}{'═' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}  🎉  ĐÓNG GÓI NHẸ HOÀN TẤT!{C.RESET}")
    print(f"{C.GREEN}{'═' * 60}{C.RESET}")
    print()
    print(f"  📦 File ZIP:      {C.CYAN}{zip_path.name} ({size_mb:.1f} MB){C.RESET}")
    print(f"  📁 Thư mục:       {C.CYAN}{OUTPUT_DIR}{C.RESET}")
    print(f"  📄 Số files:      {C.CYAN}{file_count}{C.RESET}")
    print()
    print(f"  {C.YELLOW}Để triển khai trên máy mới:{C.RESET}")
    print(f"  1. Cài Python 3.9+  (python.org)")
    print(f"  2. Cài PostgreSQL 13+")
    print(f"  3. Giải nén → chạy {C.BOLD}INSTALL.bat{C.RESET}")
    print(f"  4. Sau đó khởi động bằng {C.BOLD}RUN.bat{C.RESET} hoặc {C.BOLD}RUN_GUI.bat{C.RESET}")
    print()
    print(f"  {C.GREEN}So sánh với bản PyInstaller:{C.RESET}")
    print(f"    PyInstaller: 77.6 MB, khởi động 5-10s")
    print(f"    Light:       {size_mb:.1f} MB, khởi động 2-3s")
    print()


def main():
    print(f"""
{C.CYAN}  ╔══════════════════════════════════════════════════════╗
  ║    ERP-VIET — Lightweight Source Package Builder      ║
  ╚══════════════════════════════════════════════════════╝{C.RESET}
""")

    # Step 1: Clean
    info("Dọn dẹp output cũ...")
    clean_output()

    # Step 2: Copy source
    print()
    info("Đang copy source code...")
    copy_files()

    # Step 3: Create scripts
    print()
    info("Tạo scripts cài đặt & khởi động...")
    create_install_bat()
    create_run_bat()
    create_run_launcher_bat()
    create_readme()

    # Step 4: ZIP
    print()
    zip_path, size_mb, file_count = create_zip()

    # Summary
    show_summary(zip_path, size_mb, file_count)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}  Đã hủy.{C.RESET}")
        sys.exit(0)
    except Exception as e:
        fail(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

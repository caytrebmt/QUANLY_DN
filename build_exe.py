#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║          ERP-VIET — Build Script                             ║
║  Đóng gói ứng dụng thành file .exe portable                 ║
║                                                              ║
║  Cách chạy:                                                  ║
║    python build_exe.py                                       ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import shutil
import subprocess
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
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

BASE_DIR = Path(__file__).parent.resolve()
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
OUTPUT_NAME = "ERP-VIET"
OUTPUT_DIR = DIST_DIR / OUTPUT_NAME

# ── Colors ─────────────────────────────────────────────────────
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


def check_pyinstaller():
    """Kiểm tra PyInstaller đã được cài chưa."""
    try:
        import PyInstaller
        ok(f"PyInstaller {PyInstaller.__version__} đã cài")
        return True
    except ImportError:
        fail("PyInstaller chưa được cài!")
        info("Đang cài PyInstaller...")
        rc = subprocess.call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
        if rc == 0:
            ok("Đã cài PyInstaller")
            return True
        fail("Không thể cài PyInstaller")
        return False


def install_requirements():
    """Đảm bảo dependencies trong requirements.txt đã được cài."""
    req_file = BASE_DIR / "requirements.txt"
    if not req_file.exists():
        fail("Không tìm thấy requirements.txt!")
        return False

    info("Đang cài/cập nhật dependencies từ requirements.txt...")
    rc = subprocess.call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
    if rc != 0:
        fail("Cài dependencies thất bại.")
        return False

    # Verify package gây lỗi gần nhất
    rc_verify = subprocess.call([sys.executable, "-c", "import flask_babel"])
    if rc_verify != 0:
        fail("Thiếu module flask_babel sau khi cài requirements.")
        return False

    ok("Dependencies đã sẵn sàng")
    return True


def clean_old_build():
    """Xóa thư mục build cũ."""
    for d in [BUILD_DIR / OUTPUT_NAME, OUTPUT_DIR]:
        if d.exists():
            info(f"Đang xóa {d.name}/...")
            shutil.rmtree(d, ignore_errors=True)
    ok("Đã dọn build cũ")


def run_pyinstaller():
    """Chạy PyInstaller với spec file."""
    spec_file = BASE_DIR / "launcher.spec"
    if not spec_file.exists():
        fail("Không tìm thấy launcher.spec!")
        return False

    info("Đang build EXE (có thể mất 3-10 phút)...")
    print()

    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--noconfirm"]
    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    if result.returncode != 0:
        fail("PyInstaller build FAILED!")
        return False

    if not OUTPUT_DIR.exists():
        fail(f"Thư mục output {OUTPUT_DIR} không tồn tại sau build!")
        return False

    ok("Build EXE thành công!")
    return True


def create_readme():
    """Tạo file hướng dẫn trong thư mục dist."""
    readme_content = f"""╔══════════════════════════════════════════════════════════════╗
║              ERP-VIET — Hướng dẫn cài đặt                    ║
║              Build: {datetime.now().strftime('%Y-%m-%d %H:%M')}                          ║
╚══════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════
  BƯỚC 1: CÀI POSTGRESQL (nếu chưa có)
═══════════════════════════════════════════════════════════════

  1. Tải PostgreSQL 15+ tại:
     https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

  2. Trong quá trình cài, nhớ ghi lại:
     • Username (mặc định: postgres)
     • Password (bạn tự đặt)
     • Port (mặc định: 5432)

  3. Đảm bảo PostgreSQL service đang chạy


═══════════════════════════════════════════════════════════════
  BƯỚC 2: CHẠY ERP-VIET
═══════════════════════════════════════════════════════════════

  1. Giải nén thư mục ERP-VIET vào ổ đĩa (ví dụ: D:\\ERP-VIET)

  2. Double-click file  ERP-VIET.exe

  3. Cửa sổ cấu hình sẽ hiện ra, nhập:
     • Host: localhost (hoặc IP máy chủ DB)
     • Port: 5432
     • Database: erpmini  (sẽ tự tạo nếu chưa có)
     • Username: postgres
     • Password: (password PostgreSQL của bạn)

  4. Nhấn "Lưu và khởi động"
     → Hệ thống sẽ tự tạo database và bảng dữ liệu
     → Trình duyệt tự mở tại http://localhost:5000


═══════════════════════════════════════════════════════════════
  BƯỚC 3: ĐĂNG NHẬP
═══════════════════════════════════════════════════════════════

  Tài khoản mặc định:
  ┌─────────────┬──────────────┬──────────────────────────┐
  │   Vai trò    │  Username    │  Password                 │
  ├─────────────┼──────────────┼──────────────────────────┤
  │  Admin      │  admin       │  Xem trong console cài đặt│
  │  Kế toán    │  ketoan      │  Xem trong console cài đặt│
  └─────────────┴──────────────┴──────────────────────────┘

  ⚠ Đổi mật khẩu ngay sau lần đăng nhập đầu tiên!


═══════════════════════════════════════════════════════════════
  TRUY CẬP TỪ MÁY KHÁC TRONG MẠNG LAN
═══════════════════════════════════════════════════════════════

  Các máy khác trong cùng mạng LAN có thể truy cập:
    http://<IP-máy-chạy-ERP>:5000

  Ví dụ: http://192.168.1.100:5000


═══════════════════════════════════════════════════════════════
  XỬ LÝ SỰ CỐ
═══════════════════════════════════════════════════════════════

  • Nếu không kết nối được DB:
    → Kiểm tra PostgreSQL đang chạy (Services → postgresql)
    → Kiểm tra username/password

  • Nếu port 5000 bị chiếm:
    → Đổi port trong cửa sổ cấu hình

  • Xem log lỗi: file launcher.log (cùng thư mục ERP-VIET.exe)

  • Đổi cấu hình DB: Click phải icon ERP trên khay hệ thống
    → "Cấu hình dữ liệu"
"""
    readme_path = OUTPUT_DIR / "HUONG_DAN_CAI_DAT.txt"
    readme_path.write_text(readme_content, encoding="utf-8")
    ok("Đã tạo HUONG_DAN_CAI_DAT.txt")


def create_zip():
    """Nén thư mục dist thành file ZIP."""
    zip_name = f"ERP-VIET_{datetime.now().strftime('%Y%m%d')}.zip"
    zip_path = DIST_DIR / zip_name

    if zip_path.exists():
        zip_path.unlink()

    info(f"Đang nén thành {zip_name}...")

    file_count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for f in files:
                full_path = os.path.join(root, f)
                arc_name = os.path.join(OUTPUT_NAME, os.path.relpath(full_path, OUTPUT_DIR))
                zf.write(full_path, arc_name)
                file_count += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    ok(f"Đã tạo {zip_name} ({size_mb:.1f} MB, {file_count} files)")
    return zip_path


def show_summary(zip_path):
    """Hiển thị tóm tắt."""
    print()
    print(f"{C.GREEN}{'═' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}  🎉  ĐÓNG GÓI HOÀN TẤT!{C.RESET}")
    print(f"{C.GREEN}{'═' * 60}{C.RESET}")
    print()
    print(f"  📂 Thư mục output:  {C.CYAN}{OUTPUT_DIR}{C.RESET}")
    print(f"  📦 File ZIP:        {C.CYAN}{zip_path}{C.RESET}")
    print(f"  📄 Hướng dẫn:       {C.CYAN}{OUTPUT_DIR / 'HUONG_DAN_CAI_DAT.txt'}{C.RESET}")
    print()
    print(f"  {C.YELLOW}Để triển khai trên máy mới:{C.RESET}")
    print(f"  1. Copy file ZIP sang máy mới")
    print(f"  2. Giải nén → chạy ERP-VIET.exe")
    print(f"  3. Cài PostgreSQL nếu chưa có")
    print()


def main():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"""
{C.CYAN}  ╔══════════════════════════════════════════════════════╗
  ║        ERP-VIET — Build Portable Package             ║
  ╚══════════════════════════════════════════════════════╝{C.RESET}
""")

    # Step 1: Check PyInstaller
    info("Kiểm tra PyInstaller...")
    if not check_pyinstaller():
        sys.exit(1)

    # Step 2: Clean
    info("Dọn dẹp build cũ...")
    clean_old_build()

    # Step 3: Install app dependencies
    info("Kiểm tra dependencies ứng dụng...")
    if not install_requirements():
        sys.exit(1)

    # Step 4: Build
    print()
    if not run_pyinstaller():
        sys.exit(1)

    # Step 5: Create README
    print()
    info("Tạo hướng dẫn cài đặt...")
    create_readme()

    # Step 6: Create ZIP
    print()
    zip_path = create_zip()

    # Summary
    show_summary(zip_path)


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

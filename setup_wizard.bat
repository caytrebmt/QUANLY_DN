@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

title ERPmini Setup Wizard

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║         ERPmini - Setup Wizard                           ║
echo  ║   Tro ly cai dat tu dong cho Windows                     ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: file .bat
cd /d "%~dp0"

:: Python
echo  [*] Kiem tra Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [!] KHONG TIM THAY PYTHON!
    echo.
    echo  Vui long cai dat Python 3.9+ tu:
    echo  https://www.python.org/downloads/
    echo.
    echo  Luu y: Tick chon "Add Python to PATH" khi cai dat!
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo  [OK] Tim thay: %PY_VER%

:: Python >= 3.9
python -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [!] Python qua cu. Can Python 3.9+
    echo  Tai tai: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: setup wizard
echo.
echo  [*] Khoi dong Setup Wizard...
echo.
python setup_wizard.py

if %errorlevel% neq 0 (
    echo.
    echo  [!] Setup Wizard ket thuc voi loi.
    echo  Vui long kiem tra thong bao loi phia tren.
    pause
    exit /b 1
)

endlocal

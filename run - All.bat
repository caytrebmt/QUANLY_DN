@echo off
title ERP-VIET Master Control
color 0A
cls

echo ================================================
echo         ERP-VIET - Khoi dong he thong
echo ================================================
echo.

:: 1. Mo cua so moi de chay Frontend (Webshop)
echo [*] Dang mo Frontend trong cua so moi...
start "ERP-VIET Frontend" cmd /k "cd /d D:\Soft\Project\ERPACC\webshop && npm run dev"

:: 2. Chay Backend ngay tai cua so hien tai
echo [*] Dang khoi dong Backend...
cd /d "%~dp0"
call venv\Scripts\activate.bat

set PYTHONWARNINGS=ignore::UserWarning
set SQLALCHEMY_WARN_20=0

echo [*] Truy cap Backend: http://localhost:5000
echo [*] Nhan Ctrl+C de dung server
echo.

python run.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Backend dung do loi. Ma loi: %ERRORLEVEL%
    pause
)

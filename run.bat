@echo off
title ERP-VIET Server
color 0A
cls

echo ================================================
echo         ERP-VIET - Khoi dong he thong
echo ================================================
echo.

:: Chuyen den thu muc project
cd /d "%~dp0"

:: Kich hoat virtual environment
call venv\Scripts\activate.bat

:: Tat warning khong can thiet
set PYTHONWARNINGS=ignore::UserWarning
set SQLALCHEMY_WARN_20=0

echo [*] Dang khoi dong server...
echo [*] Truy cap: http://localhost:5000
echo [*] Nhan Ctrl+C de dung server
echo.

:: Chay server
python run.py
:: Neu loi thi giu cua so lai
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Server dung do loi. Ma loi: %ERRORLEVEL%
    pause
)

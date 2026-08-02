@echo off
chcp 65001 >nul
title ERP-Server
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║          ERP-VIET - Starting...              ║
echo  ╚══════════════════════════════════════════════╝
echo.
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo  [INFO] Ứng dụng sẽ chạy tại: http://localhost:5000
echo  [INFO] Nhấn Ctrl+C để dừng server
echo.
timeout /t 2 >nul
start http://localhost:5000
python run.py
pause

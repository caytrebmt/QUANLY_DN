#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo ""
echo "  ERPmini đang khởi động..."
echo "  Truy cập: http://localhost:5000"
echo "  Nhấn Ctrl+C để dừng"
echo ""
python run.py

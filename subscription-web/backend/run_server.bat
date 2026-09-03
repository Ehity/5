@echo off
cd /d c:\Python\subscription-web\backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 > server.log 2>&1

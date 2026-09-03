@echo off
chcp 65001 >nul
title Сбер.Сканер Подписок

echo Запуск Сбер.Сканер Подписок...
echo.

REM Если сервер ещё не запущен - поднимаем его
powershell -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo Поднимаем сервер http://127.0.0.1:8000 ...
    start "Сканер Подписок - сервер" /min cmd /c "cd /d c:\Python\subscription-web\backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000"
    timeout /t 3 /nobreak >nul
)

echo Открываем страницу в браузере...
start http://127.0.0.1:8000

echo.
echo Готово! Страница: http://127.0.0.1:8000
echo (сервер работает в свёрнутом окне; закройте его, чтобы остановить)
timeout /t 5 >nul

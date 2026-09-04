@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Сканер подписок
cd /d "%~dp0"

echo ============================================
echo         СКАНЕР ПОДПИСОК (Кейс 4)
echo ============================================
echo.
python main.py data\demo_statement.csv --interactive

echo.
pause

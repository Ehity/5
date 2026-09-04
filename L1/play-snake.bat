@echo off
chcp 65001 >nul
rem === Snake game launcher: double-click to play ===

rem Go to the project folder located next to this file
cd /d "%~dp0snake-game"
if errorlevel 1 (
    echo [Error] Folder snake-game not found next to this file.
    pause
    exit /b 1
)

rem If the server is already running - just open the game in browser
curl -s -o NUL --max-time 2 http://localhost:5173/
if %errorlevel%==0 (
    echo Server is already running - opening the game...
    start "" http://localhost:5173
    timeout /t 3 >nul
    exit /b 0
)

rem On first run install dependencies automatically
if not exist node_modules (
    echo First run: installing dependencies, please wait a minute...
    call npm install
)

rem Start server minimized; browser opens automatically
echo Starting the game... Your browser will open in a few seconds.
start "Snake - server" /min cmd /c "npm run dev"

echo.
echo ==================================================
echo   Game started! You can close this window.
echo   To stop the game - close the minimized window
echo   titled "Snake - server".
echo ==================================================
echo.
timeout /t 8 >nul
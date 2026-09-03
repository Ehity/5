@echo off
cd /d c:\Python\subscription-web\frontend
echo [%date% %time%] npm install... > npm_install.log
call npm install --no-audit --no-fund >> npm_install.log 2>&1
echo [%date% %time%] DONE rc=%errorlevel% >> npm_install.log
call npm run build >> npm_install.log 2>&1
echo [%date% %time%] BUILD rc=%errorlevel% >> npm_install.log

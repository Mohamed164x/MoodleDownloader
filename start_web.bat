@echo off
setlocal
chcp 65001 >nul
title KFU Moodle Downloader (Web)
cd /d "%~dp0\web"

python -c "import flask, requests, bs4" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install flask requests beautifulsoup4
)

echo.
echo Starting server... (close this window to stop)
echo.
echo On your phone, open your browser and go to the address shown below.
echo If the server runs on 0.0.0.0 it prints your LAN IP - use that.
echo.
python server.py
pause
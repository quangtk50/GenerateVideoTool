@echo off
REM Cai dat lan dau tren Windows
cd /d "%~dp0"
where ffmpeg >nul 2>nul || echo [!] Chua co FFmpeg. Chay: winget install Gyan.FFmpeg  (roi mo lai cua so)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
python -m app.cli check
echo.
echo Xong. Mo file .env de dien API key, roi chay start.bat
pause

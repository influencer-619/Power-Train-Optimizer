@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
set PYTHONPATH=%CD%
echo.
echo PowerTrain Optimizer starting...
echo This PC:     http://127.0.0.1:8765/  (port may vary)
echo Network:     open Settings in the app, or data\ACCESS_URLS.txt after start
echo Others on Wi-Fi can use the Network URL while this window stays open.
echo Click Quit App to stop (keeps running if you only close the browser).
echo.
python -m backend.launcher
echo.
echo PowerTrain Optimizer stopped.
endlocal

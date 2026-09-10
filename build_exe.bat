@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  PowerTrain Optimizer — build EXE from CURRENT source
echo ============================================================

if not exist .venv (
  echo Creating .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo Failed to create .venv
    exit /b 1
  )
)
call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo Failed to activate .venv
  exit /b 1
)

python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo pip install requirements failed
  exit /b 1
)
python -m pip install -q pyinstaller
if errorlevel 1 (
  echo pip install pyinstaller failed
  exit /b 1
)

REM The shipped UI is the static SPA in frontend\dist (app.js / charts.js / styles.css).
REM Vite React output goes to frontend\dist-react and is NOT packaged — do not overwrite dist.
echo Packaging frontend\dist static SPA (source of truth for the EXE UI).
if not exist "frontend\dist\index.html" (
  echo ERROR: frontend\dist\index.html missing — cannot build EXE.
  exit /b 1
)

REM Running EXE locks dist\PowerTrainOptimizer.exe and blocks overwrite with an OLD binary left behind.
echo Stopping any running PowerTrainOptimizer.exe so the new build can replace it...
taskkill /F /IM PowerTrainOptimizer.exe >nul 2>&1
REM Brief pause so Windows releases the EXE file lock (timeout fails under some redirected shells)
ping -n 3 127.0.0.1 >nul

if exist "dist\PowerTrainOptimizer.exe" (
  echo Removing previous dist\PowerTrainOptimizer.exe ...
  del /F /Q "dist\PowerTrainOptimizer.exe" >nul 2>&1
  if exist "dist\PowerTrainOptimizer.exe" (
    echo ERROR: Cannot delete dist\PowerTrainOptimizer.exe — still locked.
    echo Close the app / Task Manager, then run this script again.
    exit /b 1
  )
)

REM Wipe PyInstaller work so Analysis always re-scans backend + config source
if exist "build\PowerTrainOptimizer" (
  echo Cleaning build\PowerTrainOptimizer ...
  rmdir /s /q "build\PowerTrainOptimizer" >nul 2>&1
)

set PYTHONPATH=%CD%
echo.
echo Running PyInstaller (this uses backend\, config\, frontend\dist\) ...
pyinstaller --noconfirm --clean PowerTrainOptimizer.spec
if errorlevel 1 (
  echo.
  echo ERROR: PyInstaller failed — EXE was NOT updated.
  exit /b 1
)

if not exist "%CD%\dist\PowerTrainOptimizer.exe" (
  echo ERROR: Build finished but dist\PowerTrainOptimizer.exe is missing.
  exit /b 1
)

copy /Y "%CD%\docs\HOW_TO_SHARE.txt" "%CD%\dist\HOW_TO_SHARE.txt" >nul 2>&1

echo.
echo ============================================================
echo  Build OK — latest code packaged:
echo    %CD%\dist\PowerTrainOptimizer.exe
for %%F in ("%CD%\dist\PowerTrainOptimizer.exe") do echo    Size: %%~zF bytes  ^|  %%~tF
echo ============================================================
endlocal
exit /b 0

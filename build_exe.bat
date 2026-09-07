@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m pip install pyinstaller

REM Rebuild React UI if npm is available; otherwise keep existing frontend/dist SPA
where npm >nul 2>nul
if %ERRORLEVEL%==0 (
  pushd frontend
  call npm install
  call npm run build
  if exist dist-react\index.html (
    echo React build produced dist-react — copy over dist only after verifying parity.
  )
  popd
) else (
  echo npm not found — packaging existing frontend\dist static SPA.
)

set PYTHONPATH=%CD%
pyinstaller --noconfirm --clean PowerTrainOptimizer.spec
echo.
if exist "%CD%\dist\PowerTrainOptimizer.exe" (
  copy /Y "%CD%\docs\HOW_TO_SHARE.txt" "%CD%\dist\HOW_TO_SHARE.txt" >nul
  echo EXE location: %CD%\dist\PowerTrainOptimizer.exe
  echo Also copied:  %CD%\dist\HOW_TO_SHARE.txt
) else (
  echo Build may have failed — EXE not found.
)
endlocal

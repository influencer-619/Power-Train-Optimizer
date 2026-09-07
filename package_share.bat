@echo off
setlocal
cd /d "%~dp0"

REM Build portable EXE then copy a ready-to-share folder
call build_exe.bat
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

set SHARE=%CD%\dist\PowerTrain_Share
if exist "%SHARE%" rmdir /s /q "%SHARE%"
mkdir "%SHARE%"
copy /Y "%CD%\dist\PowerTrainOptimizer.exe" "%SHARE%\PowerTrainOptimizer.exe" >nul
copy /Y "%CD%\docs\HOW_TO_SHARE.txt" "%SHARE%\HOW_TO_SHARE.txt" >nul
copy /Y "%CD%\docs\HOW_TO_SHARE.txt" "%CD%\dist\HOW_TO_SHARE.txt" >nul

echo.
echo ============================================================
echo  Share this folder with anyone (USB / email / shared drive):
echo    %SHARE%
echo.
echo  Contents:
echo    PowerTrainOptimizer.exe   — double-click, no install
echo    HOW_TO_SHARE.txt          — local + network instructions
echo ============================================================
endlocal

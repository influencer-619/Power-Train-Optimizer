@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  PowerTrain Optimizer — package share folder
echo  (rebuilds EXE from current source first)
echo ============================================================

call "%~dp0build_exe.bat"
if errorlevel 1 (
  echo.
  echo Share package aborted — EXE build failed. Fix the error above and retry.
  exit /b 1
)

if not exist "%CD%\dist\PowerTrainOptimizer.exe" (
  echo ERROR: dist\PowerTrainOptimizer.exe missing after build.
  exit /b 1
)

set SHARE=%CD%\dist\PowerTrain_Share
if exist "%SHARE%" rmdir /s /q "%SHARE%"
mkdir "%SHARE%"
copy /Y "%CD%\dist\PowerTrainOptimizer.exe" "%SHARE%\PowerTrainOptimizer.exe" >nul
if errorlevel 1 (
  echo ERROR: Could not copy EXE into share folder.
  exit /b 1
)
copy /Y "%CD%\docs\HOW_TO_SHARE.txt" "%SHARE%\HOW_TO_SHARE.txt" >nul
copy /Y "%CD%\docs\HOW_TO_SHARE.txt" "%CD%\dist\HOW_TO_SHARE.txt" >nul
if exist "%CD%\docs\PowerTrain_Optimizer_User_Guide.docx" (
  copy /Y "%CD%\docs\PowerTrain_Optimizer_User_Guide.docx" "%SHARE%\PowerTrain_Optimizer_User_Guide.docx" >nul
)

echo.
echo ============================================================
echo  Share this folder (USB / email / shared drive):
echo    %SHARE%
echo.
echo  Contents:
echo    PowerTrainOptimizer.exe              — double-click, no install
echo    HOW_TO_SHARE.txt                     — local + network instructions
if exist "%SHARE%\PowerTrain_Optimizer_User_Guide.docx" (
  echo    PowerTrain_Optimizer_User_Guide.docx — detailed user guide
)
for %%F in ("%SHARE%\PowerTrainOptimizer.exe") do echo.
for %%F in ("%SHARE%\PowerTrainOptimizer.exe") do echo  EXE timestamp: %%~tF
echo ============================================================
endlocal
exit /b 0

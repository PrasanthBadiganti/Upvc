@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"

echo =============================================
echo       UPVC Pro - One-time Local Setup
echo =============================================

echo.
echo This version uses a prebuilt frontend.
echo Node.js and npm are NOT required.
echo.

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)
if not defined PY_CMD (
  echo ERROR: Python 3 was not found.
  echo Install Python 3.11 or newer and enable "Add Python to PATH".
  pause
  exit /b 1
)

cd /d "%ROOT%backend"
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating Python virtual environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :failed
) else (
  echo [1/3] Python virtual environment already exists.
)

echo [2/3] Installing backend packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :failed

echo [3/3] Verifying frontend and backend...
if not exist "%ROOT%frontend\dist\index.html" (
  echo ERROR: Prebuilt frontend is missing: frontend\dist\index.html
  goto :failed
)
".venv\Scripts\python.exe" -c "from app.main import app; print('Application import successful')"
if errorlevel 1 goto :failed

echo.
echo Setup completed successfully.
echo Run start-local.bat to open the application.
pause
exit /b 0

:failed
echo.
echo Setup failed. Copy the complete error shown above when requesting support.
pause
exit /b 1

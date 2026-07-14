@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"

if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
  echo Dependencies are not installed. Starting one-time setup...
  call "%ROOT%setup-local.bat"
  if errorlevel 1 exit /b 1
)

if not exist "%ROOT%frontend\dist\index.html" (
  echo ERROR: Prebuilt frontend files are missing.
  pause
  exit /b 1
)

echo =============================================
echo             UPVC Pro is starting
echo =============================================
echo Application: http://127.0.0.1:8000
echo API docs:   http://127.0.0.1:8000/docs
echo.
echo Keep this window open while using the software.
echo Press Ctrl+C to stop it.
echo.

start "" http://127.0.0.1:8000
cd /d "%ROOT%backend"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

if errorlevel 1 (
  echo.
  echo The application stopped because of an error.
  pause
)
endlocal

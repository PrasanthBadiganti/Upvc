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
set "PORT=8000"
"%ROOT%backend\.venv\Scripts\python.exe" -c "import socket,sys; s=socket.socket(); sys.exit(0 if s.connect_ex(('127.0.0.1',8000)) else 1)"
if errorlevel 1 (
  set "PORT=8001"
  echo Port 8000 is already in use. Starting UPVC Pro on port 8001.
)
echo Application: http://127.0.0.1:%PORT%
echo API docs:   http://127.0.0.1:%PORT%/docs
echo.
echo Keep this window open while using the software.
echo Press Ctrl+C to stop it.
echo.

start "" http://127.0.0.1:%PORT%
cd /d "%ROOT%backend"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%

if errorlevel 1 (
  echo.
  echo The application stopped because of an error.
  pause
)
endlocal

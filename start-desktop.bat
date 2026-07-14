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

echo Installing desktop runtime packages if needed...
"%ROOT%backend\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%ROOT%desktop\requirements-desktop.txt"
if errorlevel 1 (
  echo.
  echo Desktop runtime setup failed.
  pause
  exit /b 1
)

cd /d "%ROOT%"
"%ROOT%backend\.venv\Scripts\python.exe" "%ROOT%desktop\upvc_desktop.py"
endlocal

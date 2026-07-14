@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"

echo =============================================
echo        UPVC Pro - Desktop Build
echo =============================================

if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
  call "%ROOT%setup-local.bat"
  if errorlevel 1 exit /b 1
)

if not exist "%ROOT%frontend\dist\index.html" (
  echo ERROR: Prebuilt frontend is missing: frontend\dist\index.html
  pause
  exit /b 1
)

echo [1/3] Installing desktop build packages...
"%ROOT%backend\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%ROOT%desktop\requirements-desktop.txt"
if errorlevel 1 goto :failed

echo [2/3] Building Windows desktop app...
cd /d "%ROOT%"
"%ROOT%backend\.venv\Scripts\python.exe" -m PyInstaller ^
  --noconfirm ^
  --windowed ^
  --name "UPVC Pro" ^
  --workpath "%ROOT%build-desktop-cache" ^
  --distpath "%ROOT%desktop-dist" ^
  --paths "%ROOT%backend" ^
  --add-data "%ROOT%backend\app;backend\app" ^
  --add-data "%ROOT%frontend\dist;frontend\dist" ^
  "%ROOT%desktop\upvc_desktop.py"
if errorlevel 1 goto :failed

echo [3/3] Creating installer if Inno Setup is available...
where iscc >nul 2>nul
if errorlevel 1 (
  echo Inno Setup Compiler not found. EXE build is ready at:
  echo %ROOT%desktop-dist\UPVC Pro\UPVC Pro.exe
  goto :done
)
iscc "%ROOT%installer\upvc-pro.iss"
if errorlevel 1 goto :failed

:done
echo.
echo Desktop build completed.
echo App folder: %ROOT%desktop-dist\UPVC Pro
echo Installer:  %ROOT%installer\Output
pause
exit /b 0

:failed
echo.
echo Desktop build failed. Copy the full error above when requesting support.
pause
exit /b 1

@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"

if not exist "%ROOT%frontend\node_modules\.bin\vite.cmd" (
  echo Frontend packages are not installed. Starting setup...
  call "%ROOT%setup-frontend.bat"
  if errorlevel 1 exit /b 1
)

echo =============================================
echo       UPVC Pro - Frontend Build
echo =============================================
echo Existing frontend\dist will be backed up before the new build.
echo.

cd /d "%ROOT%frontend"
npm run build
if errorlevel 1 goto :failed

echo.
echo Frontend build completed.
echo FastAPI will serve the new frontend\dist after restart.
pause
exit /b 0

:failed
echo.
echo Frontend build failed. The previous dist backup is in frontend\dist-backups.
pause
exit /b 1

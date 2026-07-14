@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"

echo =============================================
echo       UPVC Pro - Frontend Setup
echo =============================================
echo.
echo This installs Node packages for React/Vite development.
echo It does not delete frontend\dist.
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js was not found. Install Node.js 22 LTS or newer.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: npm was not found.
  pause
  exit /b 1
)

cd /d "%ROOT%frontend"
npm install
if errorlevel 1 goto :failed

echo.
echo Frontend setup completed.
echo Run start-frontend-dev.bat to work on React separately.
pause
exit /b 0

:failed
echo.
echo Frontend setup failed. Check the npm error above.
pause
exit /b 1

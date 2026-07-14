@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"

if not exist "%ROOT%frontend\node_modules\.bin\vite.cmd" (
  echo Frontend packages are not installed. Starting setup...
  call "%ROOT%setup-frontend.bat"
  if errorlevel 1 exit /b 1
)

echo =============================================
echo       UPVC Pro React Dev Server
echo =============================================
echo Frontend: http://127.0.0.1:5173
echo API proxy: http://127.0.0.1:8001
echo.
echo Keep the backend running separately.
echo.

cd /d "%ROOT%frontend"
set "VITE_API_PROXY=http://127.0.0.1:8001"
npm run dev
endlocal

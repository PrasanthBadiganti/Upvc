@echo off
REM UPVC Pro Application Launcher
REM This batch file starts the UPVC Pro application

echo ============================================================
echo UPVC Pro - Professional UPVC Business Management System
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM Check if Node/npm is installed
npm --version >nul 2>&1
if errorlevel 1 (
    echo Warning: npm is not installed. Frontend dev server won't start.
    echo You can still access the app at http://localhost:8000 after the backend starts.
)

REM Start backend in a new window
echo Starting backend server...
start "UPVC Pro Backend" cmd /k "cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

REM Wait for backend to start
echo Waiting for backend to start...
timeout /t 3 /nobreak

REM Start frontend dev server if npm is available
npm --version >nul 2>&1
if not errorlevel 1 (
    echo Starting frontend dev server...
    start "UPVC Pro Frontend" cmd /k "cd frontend && npm run dev -- --host"
)

REM Open browser
echo Opening application in browser...
timeout /t 2 /nobreak
start http://localhost:5173

echo.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo Close the command windows to stop the application.
pause

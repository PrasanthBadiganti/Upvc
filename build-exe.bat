@echo off
REM Build UPVC Pro Standalone Executable

echo ============================================================
echo UPVC Pro - Building Standalone Executable
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    pause
    exit /b 1
)

REM Install PyInstaller if not present
echo Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Ensure frontend is built
echo Building frontend...
cd frontend
call npm run build
cd ..

REM Copy frontend dist to backend static
echo Copying frontend build to backend static folder...
if exist "backend\app\static" rmdir /s /q "backend\app\static"
xcopy /E /I /Y "frontend\dist" "backend\app\static"

REM Create executable
echo.
echo Building executable...
cd backend
pyinstaller upvc_backend.spec --distpath=../dist --buildpath=build --specpath=.

if errorlevel 1 (
    echo Error building executable
    pause
    exit /b 1
)

cd ..

echo.
echo ============================================================
echo Build complete!
echo Executable location: dist\UPVC-Pro\UPVC-Pro.exe
echo ============================================================
echo.
pause

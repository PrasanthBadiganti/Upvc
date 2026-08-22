@echo off
setlocal EnableExtensions

REM Build the UPVC Pro desktop app. Mirrors the BROMS build:
REM   frontend -> kill running exe -> clear old build -> PyInstaller -> self-test
REM Output: backend\dist\UPVC Pro\UPVC Pro.exe

set "ROOT=%~dp0"
set "FRONTEND=%ROOT%frontend"
set "BACKEND=%ROOT%backend"
set "PY=%BACKEND%\.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo ERROR: virtualenv missing at %PY%
  echo Run setup-local.bat first.
  goto :err
)

echo [1/5] Building frontend...
pushd "%FRONTEND%" || goto :err
call npm.cmd run build
if errorlevel 1 goto :err
popd

echo [2/5] Closing any running app and clearing the previous build...
taskkill /IM "UPVC Pro.exe" /F >nul 2>&1

pushd "%BACKEND%" || goto :err
if exist "dist\UPVC Pro" (
  attrib -r -s -h "dist\UPVC Pro\*" /s /d >nul 2>&1
  rmdir /s /q "dist\UPVC Pro" >nul 2>&1
)
if exist "build\UPVC Pro" (
  attrib -r -s -h "build\UPVC Pro\*" /s /d >nul 2>&1
  rmdir /s /q "build\UPVC Pro" >nul 2>&1
)
if exist "dist\UPVC Pro" (
  echo Could not remove backend\dist\UPVC Pro.
  echo Close "UPVC Pro.exe", pause OneDrive sync, or delete the folder manually, then retry.
  goto :err
)

echo [3/5] Installing desktop build packages...
"%PY%" -m pip install --disable-pip-version-check -q -r "%ROOT%desktop\requirements-desktop.txt"
if errorlevel 1 goto :err

echo [4/5] Bundling with PyInstaller...
"%PY%" -m PyInstaller UPVC_Pro.spec --noconfirm --distpath dist --workpath build
if errorlevel 1 goto :err

echo [5/5] Verifying the built exe...
REM Boots the real API against a scratch data folder: schema, seeding, backup,
REM and the bundled frontend. A green build that fails here must not ship.
set "UPVC_DATA_DIR=%TEMP%\upvc-buildcheck"
if exist "%UPVC_DATA_DIR%" rmdir /s /q "%UPVC_DATA_DIR%" >nul 2>&1
"dist\UPVC Pro\UPVC Pro.exe" --self-test
if errorlevel 1 (
  echo SELF-TEST FAILED - do not ship this build.
  goto :err
)
set "UPVC_DATA_DIR="

echo.
echo Build OK. App is in: backend\dist\UPVC Pro\UPVC Pro.exe
popd
exit /b 0

:err
echo BUILD FAILED.
exit /b 1

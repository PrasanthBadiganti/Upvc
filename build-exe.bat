@echo off
REM Superseded by build-desktop.bat.
REM
REM This script used to build a separate console backend exe into a root
REM dist\ folder. Having two similarly named output folders meant a stale
REM build could be shipped by mistake, so there is now one build and one
REM output: backend\dist\UPVC Pro\UPVC Pro.exe
REM
REM Delegating rather than deleting, so existing shortcuts keep working.

echo build-exe.bat has been replaced by build-desktop.bat.
echo Output is now: backend\dist\UPVC Pro\UPVC Pro.exe
echo.
call "%~dp0build-desktop.bat" %*
exit /b %errorlevel%

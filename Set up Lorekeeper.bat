@echo off
setlocal
title Set up Lorekeeper
cd /d "%~dp0"
echo.
echo   Setting up Lorekeeper...
echo.
set "PY="
py -3 -c "import sys; raise SystemExit(sys.version_info < (3, 11))" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; raise SystemExit(sys.version_info < (3, 11))" >nul 2>&1 && set "PY=python"
if not defined PY goto nopython
%PY% "%~dp0lorekeeper" app --install
if errorlevel 1 goto failed
echo.
echo   Lorekeeper is ready.
echo.
echo   A Lorekeeper icon is now on your Desktop and in the Start menu.
echo   Lorekeeper is opening in your browser now.
echo.
echo   If you ever move this Lorekeeper folder, run "Set up Lorekeeper" again.
echo.
echo   You can close this window.
timeout /t 20 >nul
exit /b 0

:nopython
echo   Lorekeeper needs Python, a free program, version 3.11 or newer.
echo.
echo   Your browser will now open the Python download page.
echo     1. Download Python and run the installer.
echo     2. On its first screen, tick "Add python.exe to PATH", then choose "Install Now".
echo     3. When it has finished, double-click "Set up Lorekeeper" again.
echo.
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:failed
echo.
echo   Lorekeeper could not make its shortcuts.
echo   You can still open it: double-click "Open Lorekeeper" in this folder.
echo.
pause
exit /b 1

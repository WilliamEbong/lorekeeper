@echo off
rem Opens Lorekeeper without a console window. "Set up Lorekeeper" makes a Desktop icon that does the same.
cd /d "%~dp0"
set "CHECK=import sys; raise SystemExit(sys.version_info < (3, 11))"
where pyw >nul 2>&1 && py -3 -c "%CHECK%" >nul 2>&1 && (start "" pyw -3 "%~dp0lorekeeper" app & exit /b 0)
where pythonw >nul 2>&1 && python -c "%CHECK%" >nul 2>&1 && (start "" pythonw "%~dp0lorekeeper" app & exit /b 0)
echo.
echo   Lorekeeper needs Python 3.11 or newer. Double-click "Set up Lorekeeper" first.
echo.
pause

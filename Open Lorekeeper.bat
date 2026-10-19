@echo off
rem Opens Lorekeeper without a console window. "Set up Lorekeeper" makes a Desktop icon that does the same.
cd /d "%~dp0"
where pyw >nul 2>&1 && (start "" pyw -3 "%~dp0lorekeeper" app & exit /b 0)
where pythonw >nul 2>&1 && (start "" pythonw "%~dp0lorekeeper" app & exit /b 0)
echo.
echo   Lorekeeper needs Python. Double-click "Set up Lorekeeper" first.
echo.
pause

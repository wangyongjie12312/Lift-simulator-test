@echo off
REM Stops the simulator (and the API, if it was started). Safe when not running.
setlocal
cd /d "%~dp0"
call :kill server
exit /b 0

:kill
if not exist "logs\%1.pid" exit /b 0
set /p PID=<logs\%1.pid
taskkill /PID %PID% /T /F >nul 2>&1
del /q "logs\%1.pid" 2>nul
echo Stopped %1.
exit /b 0

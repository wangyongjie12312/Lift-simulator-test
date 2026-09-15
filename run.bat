@echo off
REM Safelink Lift Simulator - launcher.
REM Starts the Streamlit UI. The API is the separate lift-simulator-backend
REM repo; the UI talks to it over HTTP (Railway unless LIFTSIM_API is set).
REM The UI is started detached (pythonw = no console), so this window closes by
REM itself and nothing dies with it. Use "Stop Simulator" to stop it.
REM For no window at all, double-click "Start Simulator.vbs" instead.
setlocal
cd /d "%~dp0"

if "%~d0"=="\\" (
  echo This folder is on a network share. Copy it to a local disk first.
  pause & exit /b 1
)

set UI_PORT=8501
set PY=python
set PYW=pythonw
if exist "python\python.exe"  set PY=python\python.exe
if exist "python\pythonw.exe" set PYW=python\pythonw.exe
if not exist "logs" mkdir logs

REM Already running? Just bring the browser back up.
call :ping %UI_PORT% /_stcore/health
if not errorlevel 1 (
  start "" "http://localhost:%UI_PORT%/"
  exit /b 0
)

echo Starting the simulator...
del /q "logs\server.pid" 2>nul
start "" "%PYW%" "serve.py" ui
call :waitfor %UI_PORT% /_stcore/health 40 "the interface"
if errorlevel 1 goto failed

start "" "http://localhost:%UI_PORT%/"
exit /b 0

:ping
%PY% -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:%1%2',timeout=1)" >nul 2>&1
exit /b %errorlevel%

:waitfor
set /a N=0
:waitloop
call :ping %1 %2
if not errorlevel 1 exit /b 0
set /a N+=1
if %N% geq %3 (
  echo %~4 did not start within %3 seconds.
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto waitloop

:failed
echo See logs\server.log
pause
exit /b 1

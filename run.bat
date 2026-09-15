@echo off
REM Safelink Lift Simulator - launcher.
REM Two processes: the API (the domain) and the Streamlit UI. The API goes
REM FIRST - the UI holds no domain code and has nothing to show without it.
REM Both are started detached (pythonw = no console), so this window closes by
REM itself and nothing dies with it. Use "Stop Simulator" to stop them.
REM For no window at all, double-click "Start Simulator.vbs" instead.
setlocal
cd /d "%~dp0"

if "%~d0"=="\\" (
  echo This folder is on a network share. Copy it to a local disk first.
  pause & exit /b 1
)

REM The API listens on 127.0.0.1 only, on purpose: it has no authentication,
REM so it must never be reachable from the rest of the network. Only the UI
REM port is meant to be shared.
set API_PORT=8000
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
del /q "logs\api.pid" "logs\server.pid" 2>nul
start "" "%PYW%" "serve.py" api
call :waitfor %API_PORT% /api/health 30 "the API"
if errorlevel 1 goto failed

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
echo See logs\api.log and logs\server.log
pause
exit /b 1

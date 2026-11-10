@echo off
rem Launch the Linux Lab Python backend on the host.
rem Usage: start-server.cmd [port]   (default port: 8080)
setlocal
cd /d "%~dp0"

set "PORT=%~1"
if "%PORT%"=="" set "PORT=8080"

set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo Virtual environment not found at .venv\.
  echo Create it first: py -3.12 -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
  exit /b 1
)

set "LAB_HOST_RUNTIME=1"
echo Starting Linux Lab backend on http://127.0.0.1:%PORT% ...
"%PYTHON%" backend\desktop_server.py --port %PORT%
endlocal

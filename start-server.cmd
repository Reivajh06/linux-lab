@echo off
rem Launch the Linux Lab Python backend on the host (no Docker Compose app container).
rem Usage: start-server.cmd [port]
rem The port defaults to LAB_PORT from .env, or 8080.
rem On first run this creates .venv, installs the backend requirements and builds the UI.
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem --- Port: argument, then LAB_PORT from .env, then 8080 ---------------------------
set "PORT=%~1"
if "%PORT%"=="" if exist .env (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="LAB_PORT" set "PORT=%%B"
  )
)
if "%PORT%"=="" set "PORT=8080"

rem Fail early with a clear message instead of a uvicorn bind error.
powershell -NoProfile -Command "if (Get-NetTCPConnection -State Listen -LocalPort %PORT% -ErrorAction SilentlyContinue) { exit 1 }"
if errorlevel 1 (
  echo ERROR: Port %PORT% is already in use.
  echo Pass another port ^(start-server.cmd 8090^) or set LAB_PORT in .env.
  exit /b 1
)

rem --- Python virtual environment --------------------------------------------------
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  set "BASE="
  py -3.12 -c "" >nul 2>&1 && set "BASE=py -3.12"
  if not defined BASE py -3 -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>&1 && set "BASE=py -3"
  if not defined BASE python -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>&1 && set "BASE=python"
  if not defined BASE (
    echo ERROR: Python 3.12 or newer was not found. Install it from https://www.python.org/downloads/
    exit /b 1
  )
  echo Creating virtual environment in .venv with !BASE! ...
  !BASE! -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create the virtual environment.
    exit /b 1
  )
)

rem Reinstall only when requirements.txt changed since the last successful install.
set "STAMP=.venv\requirements.installed"
fc /b backend\requirements.txt "%STAMP%" >nul 2>&1
if errorlevel 1 (
  echo Installing backend requirements...
  "%PYTHON%" -m pip install --disable-pip-version-check -q -r backend\requirements-dev.txt
  if errorlevel 1 (
    echo ERROR: pip install failed. See the output above.
    exit /b 1
  )
  copy /y backend\requirements.txt "%STAMP%" >nul
)

rem --- Frontend ---------------------------------------------------------------------
if not exist frontend\dist\index.html (
  where pnpm >nul 2>&1
  if errorlevel 1 (
    echo WARNING: frontend\dist is missing and pnpm was not found; only /api will work.
    echo Install pnpm and run: pnpm install ^&^& pnpm build:frontend
  ) else (
    echo Building the frontend ^(first run only^)...
    call pnpm install --frozen-lockfile
    if not errorlevel 1 call pnpm build:frontend
    if errorlevel 1 echo WARNING: Frontend build failed; only /api will work.
  )
)

rem --- Run ------------------------------------------------------------------------
set "LAB_HOST_RUNTIME=1"
echo Starting Linux Lab backend on http://127.0.0.1:%PORT% ...
"%PYTHON%" backend\desktop_server.py --port %PORT%
endlocal

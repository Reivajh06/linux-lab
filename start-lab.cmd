@echo off
rem Double-click to launch Linux Lab in the browser. Arguments go to start-lab.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-lab.ps1" %*
set "status=%ERRORLEVEL%"
pause
exit /b %status%

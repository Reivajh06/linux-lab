$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Create .venv and install backend requirements plus PyInstaller first. See README.md.' }
Push-Location $projectRoot
try {
    & $pythonExe -m PyInstaller --noconfirm --clean --onedir --console --name linux-lab-server --distpath backend-dist --workpath backend-build --paths backend --collect-all uvicorn --collect-all websockets --hidden-import win32timezone --hidden-import win32pipe --hidden-import win32file --hidden-import docker.transport.npipeconn backend/desktop_server.py
    if ($LASTEXITCODE -ne 0) { throw 'Backend packaging failed' }
} finally { Pop-Location }

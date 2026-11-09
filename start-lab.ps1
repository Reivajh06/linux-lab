# Launch Linux Lab as a local web app (Docker Compose) and print the URL to open.
#
#   .\start-lab.ps1            start (or refresh) the app and open it in the browser
#   .\start-lab.ps1 -NoBrowser only print the URL
#   .\start-lab.ps1 -Stop      stop the app (learner containers keep their files)
#
# Courses, notebook pages and lab files are mounted from this folder, so editing them
# only needs a re-run of this script. Code changes are rebuilt automatically; unchanged
# code reuses Docker's build cache and takes a few seconds.
param([switch]$NoBrowser, [switch]$Stop)

# Not 'Stop': in Windows PowerShell 5.1 that makes Docker's normal progress output on
# stderr fatal. Failures are detected through $LASTEXITCODE instead.
$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot

function Fail($message) {
    Write-Host "ERROR: $message" -ForegroundColor Red
    exit 1
}

function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { Fail "'docker $($args -join ' ')' failed (exit $LASTEXITCODE)." }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail 'Docker is not installed. Install Docker Desktop: https://docs.docker.com/desktop/'
}
& docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail 'Docker is not running. Start Docker Desktop and try again.' }

if ($Stop) {
    Invoke-Docker compose stop app
    Write-Host 'Linux Lab stopped. Running learner environments keep their files.'
    exit 0
}

# Settings live in .env (not committed); create it from the example on first run.
if (-not (Test-Path .env)) {
    try {
        Copy-Item .env.example .env -ErrorAction Stop
    } catch {
        Fail "Could not create .env from .env.example: $($_.Exception.Message)"
    }
    Write-Host 'Created .env from .env.example (edit it to change the port or limits).'
}

# Ask Compose for the port it will publish, so .env, quoting and an exported LAB_PORT
# are resolved exactly as Compose resolves them.
$config = (& docker compose config --format json 2>$null) -join "`n"
if ($LASTEXITCODE -ne 0) { Fail 'docker compose config failed. Check docker-compose.yml and .env.' }
$port = [int](($config | ConvertFrom-Json).services.app.ports | Select-Object -First 1).published
$url = "http://localhost:$port"

# Fail early with a clear message instead of a cryptic Docker port error. The port is
# only fine when it is our own running app that already publishes it.
$listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalAddress -in @('0.0.0.0', '127.0.0.1', '::', '::1') }
if ($listener) {
    $published = & docker compose port app 8080 2>$null
    if ("$published".Trim() -ne "127.0.0.1:$port") {
        Fail "Port $port is already in use. Set another LAB_PORT in .env (for example LAB_PORT=8090)."
    }
}

& docker image inspect linux-lab-environment:local *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Building the Fedora lab image (first run only; this downloads several GB)...'
    Invoke-Docker compose build lab-image
}

Write-Host 'Building the app (cached when the code has not changed)...'
Invoke-Docker compose build app
Invoke-Docker compose up -d --no-build app
# Restart so courses and notebook pages edited since the last launch are reloaded.
Invoke-Docker compose restart app

Write-Host -NoNewline 'Waiting for Linux Lab to answer'
$deadline = (Get-Date).AddSeconds(90)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "$url/api/courses" | Out-Null
        $ready = $true
        break
    } catch {
        Write-Host -NoNewline '.'
        Start-Sleep -Seconds 2
    }
}
Write-Host ''
if (-not $ready) {
    & docker compose logs --tail 30 app
    Fail "Linux Lab did not answer at $url. See the log above."
}

Write-Host ''
Write-Host '  Linux Lab is running at:' -ForegroundColor Green
Write-Host "  $url" -ForegroundColor Cyan
Write-Host ''
Write-Host '  Stop it with: .\start-lab.ps1 -Stop'
if (-not $NoBrowser) { Start-Process $url }

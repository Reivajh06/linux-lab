#!/usr/bin/env bash
# Launch Linux Lab locally; re-run after editing courses or notebook pages.
set -euo pipefail

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

no_browser=false
stop=false
for arg in "$@"; do
    case "$arg" in
        --no-browser) no_browser=true ;;
        --stop) stop=true ;;
        *) fail "Unknown option: $arg. Usage: bash start-lab.sh [--no-browser] [--stop]" ;;
    esac
done

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
command -v docker >/dev/null 2>&1 || fail 'Docker is not installed. Install Docker with the Compose plugin.'
docker info >/dev/null 2>&1 || fail 'Docker is not running or is inaccessible. Start Docker and check your Docker permissions.'
docker compose version >/dev/null 2>&1 || fail 'Docker Compose is unavailable. Install the Docker Compose plugin.'

if "$stop"; then
    docker compose stop app || fail 'Could not stop Linux Lab.'
    printf 'Linux Lab stopped. Running learner environments keep their files.\n'
    exit 0
fi

command -v curl >/dev/null 2>&1 || fail 'curl is required to check when Linux Lab is ready. Install curl and try again.'
if [[ ! -f .env ]]; then
    cp .env.example .env || fail 'Could not create .env from .env.example.'
    printf 'Created .env from .env.example (edit it to change the port or limits).\n'
fi

# Compose gives an exported LAB_PORT priority over .env. Read values, not shell code.
if [[ ${LAB_PORT+x} ]]; then
    port=$LAB_PORT
else
    port=$(sed -n \
        -e 's/^[[:space:]]*export[[:space:]][[:space:]]*//' \
        -e 's/^[[:space:]]*LAB_PORT[[:space:]]*=[[:space:]]*//p' .env | tail -n 1)
    port=${port%%#*}
    port=$(printf '%s' "$port" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    case "$port" in
        \"*\"|\'*\') port=${port:1:${#port}-2} ;;
    esac
fi
port=${port:-8080}
case "$port" in
    *[!0-9]*) fail 'LAB_PORT must be a number between 1 and 65535.' ;;
esac
[[ ${#port} -le 5 ]] || fail 'LAB_PORT must be a number between 1 and 65535.'
port=$((10#$port))
(( port >= 1 && port <= 65535 )) || fail 'LAB_PORT must be a number between 1 and 65535.'
url="http://localhost:$port"

# A running app may already own this port. A different app port is not an exemption.
running_app=$(docker compose ps --status running --quiet app) || fail 'Could not inspect the Compose app.'
listeners=''
if command -v ss >/dev/null 2>&1; then
    listeners=$(ss -H -ltn "sport = :$port") || fail "Could not check port $port with ss."
elif command -v lsof >/dev/null 2>&1; then
    listeners=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
fi
if [[ -n "$listeners" ]]; then
    published=''
    if [[ -n "$running_app" ]]; then
        published=$(docker compose port app 8080) || fail 'Could not inspect the app port.'
    fi
    if [[ "$published" != "127.0.0.1:$port" ]]; then
        fail "Port $port is already in use. Set another LAB_PORT in .env (for example LAB_PORT=8090)."
    fi
fi

if ! docker image inspect linux-lab-environment:local >/dev/null 2>&1; then
    printf 'Building the Fedora lab image (first run only; this downloads several GB)...\n'
    docker compose build lab-image || fail 'Could not build the Fedora lab image.'
fi

printf 'Building the app (cached when the code has not changed)...\n'
docker compose build app || fail 'Could not build the app.'
docker compose up -d --no-build app || fail 'Could not start the app.'
# Reload shipped courses and notebook pages even when the app was already running.
docker compose restart app || fail 'Could not restart the app.'

printf 'Waiting for Linux Lab to answer'
deadline=$((SECONDS + 90))
ready=false
while (( SECONDS < deadline )); do
    if curl --noproxy '*' --fail --silent --output /dev/null --max-time 3 "$url/api/courses"; then
        ready=true
        break
    fi
    printf '.'
    sleep 2
done
printf '\n'
if ! "$ready"; then
    docker compose logs --tail 30 app || true
    fail "Linux Lab did not answer at $url. See the log above."
fi

printf '\n  Linux Lab is running at:\n  %s\n\n  Stop it with: bash start-lab.sh --stop\n' "$url"
if ! "$no_browser"; then
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url" >/dev/null 2>&1 || printf 'Open %s in your browser.\n' "$url"
    elif command -v open >/dev/null 2>&1; then
        open "$url" >/dev/null 2>&1 || printf 'Open %s in your browser.\n' "$url"
    fi
fi

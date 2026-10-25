#!/bin/bash
set -e
rm -f /tmp/lab-ready
export DISPLAY=:1 HOME=/home/learner USER=learner
export XDG_RUNTIME_DIR=/tmp/runtime-learner
export GTK_THEME=Adwaita:dark
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
Xvnc :1 -geometry 1440x900 -depth 24 -dpi 96 -localhost yes -SecurityTypes None -AlwaysShared &
vnc_pid=$!
trap 'kill "$vnc_pid" 2>/dev/null || true' EXIT
for attempt in $(seq 1 60); do
    if xdpyinfo -display :1 >/dev/null 2>&1; then break; fi
    sleep 0.25
done
xdpyinfo -display :1 >/dev/null
dbus-run-session -- bash -c '
    printf "%s" "$DBUS_SESSION_BUS_ADDRESS" > /tmp/linux-lab-session-bus
    if [ -f /opt/linux-lab-workspace/workspace.py ]; then
        python3 /opt/linux-lab-workspace/workspace.py configure
    fi
    openbox &
    xsetroot -solid "#1e1e1e"
    /usr/local/bin/lab-terminal &
    touch /tmp/lab-ready
    wait
'

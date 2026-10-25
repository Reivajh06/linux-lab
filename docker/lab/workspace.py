#!/usr/bin/env python3
"""Small EWMH adapter: every normal Linux window becomes an application tab."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

os.environ.setdefault("DISPLAY", ":1")
os.environ.setdefault("GTK_THEME", "Adwaita:dark")
os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-learner")
BUS = Path("/tmp/linux-lab-session-bus")
if BUS.exists():
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = BUS.read_text().strip()

OPENBOX = '''<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <focus><focusNew>yes</focusNew><followMouse>no</followMouse><focusLast>yes</focusLast></focus>
  <theme><name>Clearlooks</name><keepBorder>no</keepBorder></theme>
  <desktops><number>1</number><firstdesk>1</firstdesk></desktops>
  <keyboard>
    <keybind key="A-Tab"><action name="NextWindow"/></keybind>
    <keybind key="A-S-Tab"><action name="PreviousWindow"/></keybind>
    <keybind key="C-A-t"><action name="Execute"><command>/usr/local/bin/lab-terminal</command></action></keybind>
  </keyboard>
  <applications>
    <application class="*" type="normal"><decor>no</decor><maximized>yes</maximized><focus>yes</focus></application>
    <application class="*" type="dialog"><decor>yes</decor><position force="no"><x>center</x><y>center</y></position></application>
  </applications>
</openbox_config>
'''
TERMINAL = '''[Configuration]
FontName=Adwaita Mono 12
FontUseSystem=FALSE
FontAllowBold=TRUE
ColorForeground=#ffffff
ColorBackground=#1e1e1e
ColorCursor=#ffffff
ColorPalette=#241f31;#c01c28;#2ec27e;#f5c211;#1e78e4;#9841bb;#0ab9dc;#c0bfbc;#5e5c64;#ed333b;#57e389;#f8e45c;#51a1ff;#c061cb;#4fd2fd;#f6f5f4
ColorUseTheme=FALSE
ColorBoldUseDefault=TRUE
BackgroundMode=TERMINAL_BACKGROUND_SOLID
MiscMenubarDefault=FALSE
MiscToolbarDefault=FALSE
MiscBordersDefault=FALSE
ScrollingBar=TERMINAL_SCROLLBAR_NONE
ScrollingLines=10000
MiscCursorBlinks=TRUE
MiscCursorShape=TERMINAL_CURSOR_SHAPE_BLOCK
MiscBellUrgent=FALSE
MiscCopyOnSelect=FALSE
MiscConfirmClose=TRUE
'''


def run(args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, timeout=8)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "Linux window operation failed")
    return result.stdout


def configure():
    home = Path("/home/learner")
    config = home / ".config"
    for directory in (config / "openbox", config / "xfce4/terminal", config / "gtk-3.0"):
        directory.mkdir(parents=True, exist_ok=True)
    rc = config / "openbox/rc.xml"
    if rc.exists() and not (rc.parent / "rc.xml.before-tabs").exists():
        (rc.parent / "rc.xml.before-tabs").write_bytes(rc.read_bytes())
    rc.write_text(OPENBOX)
    (config / "xfce4/terminal/terminalrc").write_text(TERMINAL)
    (config / "gtk-3.0/settings.ini").write_text("[Settings]\ngtk-theme-name=Adwaita-dark\ngtk-application-prefer-dark-theme=true\ngtk-font-name=Adwaita Sans 11\ngtk-decoration-layout=\n"
        # Grayscale antialiasing stays crisp through VNC; subpixel colour fringes do not.
        "gtk-xft-antialias=1\ngtk-xft-hinting=1\ngtk-xft-hintstyle=hintslight\ngtk-xft-rgba=none\n")
    for key, value in (("scheme", "oblivion"), ("use-default-font", "false"),
                       ("editor-font", "Adwaita Mono 12"), ("display-line-numbers", "true")):
        run(["gsettings", "set", "org.gnome.gedit.preferences.editor", key, value], check=False)
    run(["gsettings", "set", "org.gnome.desktop.wm.preferences", "button-layout", ""], check=False)
    profile = home / ".bashrc"
    marker = "# Linux Lab tabbed terminal"
    if profile.exists() and marker not in profile.read_text():
        with profile.open("a") as handle:
            handle.write("\n" + marker + "\nexport GTK_THEME=Adwaita:dark\nexport DISPLAY=:1\nPS1='\\[\\e[1;32m\\]\\u@\\h\\[\\e[0m\\]:\\w\\$ '\n")
    return {"configured": True}


def properties(window):
    return run(["xprop", "-id", window, "_NET_WM_WINDOW_TYPE", "_NET_WM_STATE", "WM_TRANSIENT_FOR"], check=False)


def windows():
    result = []
    for line in run(["wmctrl", "-lpGx"]).splitlines():
        parts = line.split(None, 9)
        if len(parts) < 9:
            continue
        window, desktop, pid, x, y, width, height, wm_class, host = parts[:9]
        title = parts[9] if len(parts) > 9 else wm_class
        props = properties(window)
        if "_NET_WM_WINDOW_TYPE_DIALOG" in props or "_NET_WM_WINDOW_TYPE_NORMAL" not in props:
            continue
        app_class = wm_class.lower()
        kind = "terminal" if "terminal" in app_class or "xterm" in app_class else "editor" if "gedit" in app_class else "browser" if any(n in app_class for n in ("firefox", "chromium", "chrome", "browser")) else "app"
        result.append({"id": window, "title": title, "kind": kind, "class_name": wm_class,
                       "width": int(width), "height": int(height), "maximized": "_NET_WM_STATE_MAXIMIZED_VERT" in props and "_NET_WM_STATE_MAXIMIZED_HORZ" in props})
    # Keep terminal tabs at the start while preserving creation order for each kind.
    result.sort(key=lambda item: item["kind"] != "terminal")
    active_output = run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], check=False)
    match = re.search(r"0x[0-9a-fA-F]+", active_output)
    active = int(match.group(), 16) if match else 0
    lookup = {int(item["id"], 16): item["id"] for item in result}
    # A save/open confirmation belongs to its parent app's tab.
    for _ in range(8):
        if active in lookup or not active:
            break
        parent = run(["xprop", "-id", hex(active), "WM_TRANSIENT_FOR"], check=False)
        match = re.search(r"0x[0-9a-fA-F]+", parent)
        active = int(match.group(), 16) if match else 0
    return {"windows": result, "active_id": lookup.get(active)}


def target(window):
    if not re.fullmatch(r"0x[0-9a-fA-F]{1,16}", window or ""):
        raise ValueError("Invalid application tab ID")
    if window not in {item["id"] for item in windows()["windows"]}:
        raise ValueError("This application is no longer open")
    return window


def maximize(window):
    run(["xprop", "-id", window, "-f", "_MOTIF_WM_HINTS", "32c", "-set", "_MOTIF_WM_HINTS", "2, 0, 0, 0, 0"], check=False)
    run(["wmctrl", "-ir", window, "-b", "add,maximized_vert,maximized_horz"], check=False)


def action(name, window=None):
    if name == "configure":
        return configure()
    if name == "list":
        return windows()
    if name == "layout":
        run(["openbox", "--reconfigure"], check=False)
        for item in windows()["windows"]:
            maximize(item["id"])
        return windows()
    if name == "activate":
        window = target(window)
        maximize(window)
        run(["wmctrl", "-ia", window])
        return {"activated": window}
    if name == "close":
        run(["wmctrl", "-ic", target(window)])
        return {"closing": window}
    commands = {"terminal": ["/usr/local/bin/lab-terminal"], "editor": ["gedit", "--new-window"], "browser": ["firefox", "--new-window", "about:blank"]}
    command = commands[name]
    with open("/tmp/linux-lab-apps.log", "ab") as logfile:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=logfile, stderr=logfile, start_new_session=True)
    return {"launching": name}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["list", "configure", "layout", "activate", "close", "terminal", "editor", "browser"])
    parser.add_argument("window", nargs="?")
    args = parser.parse_args()
    try:
        print(json.dumps(action(args.action, args.window)))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
if ! command -v wmctrl >/dev/null || ! command -v gpg >/dev/null || ! command -v gsettings >/dev/null; then
    apt-get update -qq
    apt-get install -y --no-install-recommends wmctrl gnupg gnome-themes-extra adwaita-icon-theme libglib2.0-bin dconf-gsettings-backend gsettings-desktop-schemas
fi
# Course material (ASO prácticas) uses the words list and a few process tools.
if [ ! -f /usr/share/dict/words ] || ! command -v bc >/dev/null || ! command -v htop >/dev/null || ! command -v lsof >/dev/null; then
    apt-get update -qq
    apt-get install -y --no-install-recommends wamerican bc htop lsof
fi
if ! dpkg-query -W -f='${Version}' firefox 2>/dev/null | grep -qv 'snap'; then
    install -d -m 0755 /etc/apt/keyrings
    curl --fail --silent --show-error --location https://packages.mozilla.org/apt/repo-signing-key.gpg -o /etc/apt/keyrings/packages.mozilla.org.asc
    fingerprint=$(gpg --batch --show-keys --with-colons /etc/apt/keyrings/packages.mozilla.org.asc 2>/dev/null | awk -F: '$1=="fpr"{print $10;exit}')
    test "$fingerprint" = '35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3'
    printf 'deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main\n' > /etc/apt/sources.list.d/mozilla.list
    printf 'Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n\nPackage: firefox\nPin: release o=Ubuntu\nPin-Priority: -1\n' > /etc/apt/preferences.d/mozilla
    apt-get update -qq
    apt-get install -y --no-install-recommends firefox
fi
ln -sfn /usr/bin/firefox /usr/local/bin/browser
install -d /etc/firefox/policies
printf '%s\n' '{"policies":{"OverrideFirstRunPage":"","OverridePostUpdatePage":"","DontCheckDefaultBrowser":true,"Homepage":{"URL":"about:blank","StartPage":"homepage"}}}' > /etc/firefox/policies/policies.json
rm -rf /var/lib/apt/lists/*

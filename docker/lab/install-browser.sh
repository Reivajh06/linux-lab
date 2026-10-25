#!/bin/bash
set -euo pipefail
# Firefox comes from the Fedora repositories; this only wires up the launcher and policies.
if ! command -v firefox >/dev/null; then
    dnf install -y --setopt=install_weak_deps=False firefox
    dnf clean all
fi
ln -sfn /usr/bin/firefox /usr/local/bin/browser
install -d /etc/firefox/policies
printf '%s\n' '{"policies":{"OverrideFirstRunPage":"","OverridePostUpdatePage":"","DontCheckDefaultBrowser":true,"Homepage":{"URL":"about:blank","StartPage":"homepage"}}}' > /etc/firefox/policies/policies.json

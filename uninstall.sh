#!/usr/bin/env bash
# Removes Gamepad Launcher for the current user.
set -euo pipefail

systemctl --user disable --now gamepad-launcher.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/gamepad-launcher.service"
rm -rf "$HOME/.local/share/gamepad-launcher"
systemctl --user daemon-reload

echo "Gamepad Launcher odinstalován."

#!/usr/bin/env bash
# Installs Gamepad Launcher for the current user (no root needed).
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/share/gamepad-launcher"
UNIT_DIR="$HOME/.config/systemd/user"

if ! id -nG | tr ' ' '\n' | grep -qx input; then
    echo "Uživatel není ve skupině 'input', launcher by neviděl ovladač."
    echo "Spusť:  sudo usermod -aG input \$USER   a pak se odhlas a znovu přihlas."
    exit 1
fi

if ! python3 -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null; then
    echo "Chybí Python GTK 3. Na Debianu/Ubuntu:  sudo apt install python3-gi gir1.2-gtk-3.0"
    exit 1
fi

mkdir -p "$DEST" "$UNIT_DIR"
install -m 755 "$SRC/launcher.py" "$DEST/launcher.py"
install -m 644 "$SRC/gamepad-launcher.service" "$UNIT_DIR/gamepad-launcher.service"

systemctl --user daemon-reload
systemctl --user enable gamepad-launcher.service
systemctl --user restart gamepad-launcher.service

echo "Hotovo. Zmáčkni Home na ovladači."

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
DIST_DIR="$ROOT_DIR/dist/linux-control-center"
BUILD_DIR="$ROOT_DIR/build/linux-control-center"
SPEC_DIR="$ROOT_DIR/build/linux-spec"
VENV_DIR="$ROOT_DIR/.venv-package-linux"

rm -rf "$DIST_DIR" "$BUILD_DIR" "$SPEC_DIR"

"$PYTHON_BIN" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name ant-build-control-center \
  --distpath "$DIST_DIR" \
  --workpath "$BUILD_DIR" \
  --specpath "$SPEC_DIR" \
  --add-data "$ROOT_DIR/config:config" \
  --add-data "$ROOT_DIR/src:src" \
  --add-data "$ROOT_DIR/icons:icons" \
  --icon "$ROOT_DIR/icons/ant-build-menu.png" \
  "$ROOT_DIR/control_center.py"

APP_DIR="$DIST_DIR/ant-build-control-center"
mkdir -p "$APP_DIR/icons"
install -m 644 "$ROOT_DIR/icons/ant-build-menu.png" "$APP_DIR/icons/ant-build-menu.png"
install -m 644 "$ROOT_DIR/icons/ant-build-menu.svg" "$APP_DIR/icons/ant-build-menu.svg"
cat > "$APP_DIR/ant-build-control-center.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Ant Build Control Center
Name[zh_CN]=Ant Build 中控中心
Comment=Apache Ant build control center
Exec=$APP_DIR/ant-build-control-center
Path=$APP_DIR
Icon=$APP_DIR/icons/ant-build-menu.png
Terminal=false
Categories=Development;Utility;
StartupNotify=true
EOF

cat > "$APP_DIR/install_desktop_entry.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
APP_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="\$HOME/.local/share/applications"
mkdir -p "\$TARGET_DIR"
install -m 755 "\$APP_DIR/ant-build-control-center.desktop" "\$TARGET_DIR/ant-build-control-center.desktop"
if [ -d "\$HOME/Desktop" ]; then
  install -m 755 "\$APP_DIR/ant-build-control-center.desktop" "\$HOME/Desktop/ant-build-control-center.desktop"
fi
echo "Desktop entry installed to \$TARGET_DIR"
EOF
chmod +x "$APP_DIR/install_desktop_entry.sh"

tar -C "$DIST_DIR" -czf "$ROOT_DIR/dist/ant-build-control-center-linux.tar.gz" ant-build-control-center
echo "Packaged: $ROOT_DIR/dist/ant-build-control-center-linux.tar.gz"

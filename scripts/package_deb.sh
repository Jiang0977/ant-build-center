#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="${VERSION:-1.0.6}"
ARCH="${ARCH:-amd64}"
APP_NAME="ant-build-control-center"
APP_DIR="$ROOT_DIR/dist/linux-control-center/$APP_NAME"
PKG_ROOT="$ROOT_DIR/dist/deb-package"
DEB_NAME="${APP_NAME}_${VERSION}_${ARCH}.deb"

if [ ! -x "$APP_DIR/$APP_NAME" ]; then
  ./scripts/package_linux.sh
fi

rm -rf "$PKG_ROOT"
mkdir -p \
  "$PKG_ROOT/DEBIAN" \
  "$PKG_ROOT/opt/$APP_NAME" \
  "$PKG_ROOT/usr/bin" \
  "$PKG_ROOT/usr/share/applications" \
  "$PKG_ROOT/usr/share/pixmaps"

cp -a "$APP_DIR/." "$PKG_ROOT/opt/$APP_NAME/"

cat > "$PKG_ROOT/usr/bin/$APP_NAME" <<'EOF'
#!/usr/bin/env bash
exec /opt/ant-build-control-center/ant-build-control-center "$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/$APP_NAME"

install -m 644 "$ROOT_DIR/icons/ant-build-menu.png" "$PKG_ROOT/usr/share/pixmaps/$APP_NAME.png"

cat > "$PKG_ROOT/usr/share/applications/$APP_NAME.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Ant Build Control Center
Name[zh_CN]=Ant Build 中控中心
Comment=Apache Ant build control center
Exec=/usr/bin/$APP_NAME
Icon=$APP_NAME
Terminal=false
Categories=Development;Utility;
StartupNotify=true
EOF

cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: $APP_NAME
Version: $VERSION
Section: devel
Priority: optional
Architecture: $ARCH
Maintainer: Jiang <jiang@example.com>
Depends: libc6, libx11-6, libxext6, libxrender1, libxft2, libxss1, libfontconfig1
Description: Ant Build Control Center
 Tk-based control center for running Apache Ant build.xml files on Linux.
EOF

cat > "$PKG_ROOT/DEBIAN/postinst" <<'EOF'
#!/usr/bin/env bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
EOF
chmod 755 "$PKG_ROOT/DEBIAN/postinst"

cat > "$PKG_ROOT/DEBIAN/postrm" <<'EOF'
#!/usr/bin/env bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
EOF
chmod 755 "$PKG_ROOT/DEBIAN/postrm"

dpkg-deb --build "$PKG_ROOT" "$ROOT_DIR/dist/$DEB_NAME"
echo "Packaged: $ROOT_DIR/dist/$DEB_NAME"

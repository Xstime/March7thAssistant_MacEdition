#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

if [ "$(uname -m)" != "arm64" ] || [ "$(uname -s)" != "Darwin" ]; then
  echo 'This build requires an Apple Silicon Mac.' >&2
  exit 1
fi

PYTHON_BIN=${MARCH7TH_BUILD_PYTHON:-python3}
"$PYTHON_BIN" tools/fetch_macos_ocr_models.py
BUILD_ROOT=${MARCH7TH_BUILD_ROOT:-/private/tmp/march7thassistant-build-$(id -u)}
mkdir -p "$BUILD_ROOT"
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$BUILD_ROOT/cache}"
"$PYTHON_BIN" -m PyInstaller --noconfirm --clean --workpath "$BUILD_ROOT/work" \
  --distpath "$BUILD_ROOT/dist" March7thAssistant-macos.spec
APP="$BUILD_ROOT/dist/March7thAssistant.app"
xattr -cr "$APP"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
echo "Built: $APP"

if [ "${1:-}" = "--dmg" ]; then
  mkdir -p "$BUILD_ROOT/dmg"
  ditto --norsrc "$APP" "$BUILD_ROOT/dmg/March7thAssistant.app"
  ln -sfn /Applications "$BUILD_ROOT/dmg/Applications"
  hdiutil create -volname March7thAssistant -srcfolder "$BUILD_ROOT/dmg" \
    -format UDZO -ov "$BUILD_ROOT/dist/March7thAssistant.dmg"
  echo "Built: $BUILD_ROOT/dist/March7thAssistant.dmg"
fi

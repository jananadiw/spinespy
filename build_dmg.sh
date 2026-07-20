#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Building SpineSpy.app with PyInstaller ==="

poetry run python - <<'PY'
import pathlib
import sys

if not ((3, 10) <= sys.version_info < (3, 14)):
    raise SystemExit(
        f"Python {sys.version.split()[0]} is unsupported. "
        "Use Python >=3.10,<3.14 for the build environment."
    )

missing = [
    path
    for path in ("pose_landmarker.task", "efficientdet_lite0.tflite", "assets")
    if not pathlib.Path(path).exists()
]
if missing:
    raise SystemExit(f"Missing required build asset(s): {', '.join(missing)}")
PY

APP_VERSION="$(
poetry run python - <<'PY'
import pathlib
import tomllib

with pathlib.Path("pyproject.toml").open("rb") as f:
    print(tomllib.load(f)["tool"]["poetry"]["version"])
PY
)"

rm -rf build dist

poetry run pyinstaller --name SpineSpy \
    --windowed \
    --clean \
    --noconfirm \
    --add-data "pose_landmarker.task:." \
    --add-data "efficientdet_lite0.tflite:." \
    --add-data "assets:assets" \
    --hidden-import rumps \
    --hidden-import cv2 \
    --hidden-import mediapipe \
    --hidden-import mediapipe.tasks.c \
    --hidden-import AppKit \
    --collect-all mediapipe \
    --osx-bundle-identifier com.jananadiw.spinespy \
    menubar_app.py

# Add LSUIElement to Info.plist (menubar-only app)
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" dist/SpineSpy.app/Contents/Info.plist 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" dist/SpineSpy.app/Contents/Info.plist

# Add camera permission
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string 'SpineSpy needs camera access to monitor your posture.'" dist/SpineSpy.app/Contents/Info.plist 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :NSCameraUsageDescription 'SpineSpy needs camera access to monitor your posture.'" dist/SpineSpy.app/Contents/Info.plist

/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString ${APP_VERSION}" dist/SpineSpy.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string ${APP_VERSION}" dist/SpineSpy.app/Contents/Info.plist 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion ${APP_VERSION}" dist/SpineSpy.app/Contents/Info.plist

CODESIGN_IDENTITY="${CODESIGN_IDENTITY:--}"
if [[ "$CODESIGN_IDENTITY" == "-" ]]; then
    echo "⚠ Building with an ad hoc signature. This local build is not notarized."
    codesign --force --deep --sign - dist/SpineSpy.app
else
    codesign \
        --force \
        --deep \
        --options runtime \
        --timestamp \
        --entitlements entitlements.plist \
        --sign "$CODESIGN_IDENTITY" \
        dist/SpineSpy.app
fi
codesign --verify --deep --strict --verbose=2 dist/SpineSpy.app

echo ""
echo "=== Creating DMG ==="
DMG_STAGING_DIR="dist/dmg"
rm -rf "$DMG_STAGING_DIR"
mkdir -p "$DMG_STAGING_DIR"
cp -R dist/SpineSpy.app "$DMG_STAGING_DIR/"
ln -s /Applications "$DMG_STAGING_DIR/Applications"

hdiutil create -volname "SpineSpy" -srcfolder "$DMG_STAGING_DIR" -ov -format UDZO SpineSpy.dmg

if [[ "$CODESIGN_IDENTITY" != "-" ]]; then
    codesign --force --timestamp --sign "$CODESIGN_IDENTITY" SpineSpy.dmg
    codesign --verify --verbose=2 SpineSpy.dmg
fi

MAX_DMG_SIZE_MB="${MAX_DMG_SIZE_MB:-200}"
DMG_SIZE_BYTES="$(stat -f%z SpineSpy.dmg)"
MAX_DMG_SIZE_BYTES="$((MAX_DMG_SIZE_MB * 1024 * 1024))"
if (( DMG_SIZE_BYTES > MAX_DMG_SIZE_BYTES )); then
    echo "SpineSpy.dmg is $((DMG_SIZE_BYTES / 1024 / 1024)) MB; limit is ${MAX_DMG_SIZE_MB} MB." >&2
    exit 1
fi

echo ""
echo "✅ Done! SpineSpy.dmg created ($((DMG_SIZE_BYTES / 1024 / 1024)) MB)"

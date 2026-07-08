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
    for path in ("pose_landmarker.task", "yolo26s.pt", "assets")
    if not pathlib.Path(path).exists()
]
if missing:
    raise SystemExit(f"Missing required build asset(s): {', '.join(missing)}")
PY

rm -rf build dist

poetry run pyinstaller --name SpineSpy \
    --windowed \
    --noconfirm \
    --add-data "pose_landmarker.task:." \
    --add-data "yolo26s.pt:." \
    --add-data "assets:assets" \
    --hidden-import rumps \
    --hidden-import cv2 \
    --hidden-import mediapipe \
    --hidden-import ultralytics \
    --hidden-import mediapipe.tasks.c \
    --collect-all mediapipe \
    --osx-bundle-identifier com.jananadiw.spinespy \
    menubar_app.py

# Add LSUIElement to Info.plist (menubar-only app)
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" dist/SpineSpy.app/Contents/Info.plist 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" dist/SpineSpy.app/Contents/Info.plist

# Add camera permission
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string 'SpineSpy needs camera access to monitor your posture.'" dist/SpineSpy.app/Contents/Info.plist 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :NSCameraUsageDescription 'SpineSpy needs camera access to monitor your posture.'" dist/SpineSpy.app/Contents/Info.plist

echo ""
echo "=== Creating DMG ==="
rm -rf dist/SpineSpy
rm -f dist/Applications
ln -s /Applications dist/Applications
trap 'rm -f dist/Applications' EXIT

hdiutil create -volname "SpineSpy" -srcfolder dist -ov -format UDZO SpineSpy.dmg

echo ""
echo "✅ Done! SpineSpy.dmg created"

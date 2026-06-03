#!/bin/bash
set -e

echo "=== Building SpineSpy.app with PyInstaller ==="
source venv/bin/activate
pip install pyinstaller

rm -rf build dist

pyinstaller --name SpineSpy \
    --windowed \
    --noconfirm \
    --add-data "pose_landmarker.task:." \
    --add-data "yolov8n.pt:." \
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
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string 'SpineSpy needs camera access to monitor your posture.'" dist/SpineSpy.app/Contents/Info.plist 2>/dev/null || true

echo ""
echo "=== Creating DMG ==="
mkdir -p dist/dmg
cp -r dist/SpineSpy.app dist/dmg/
ln -s /Applications dist/dmg/Applications

hdiutil create -volname "SpineSpy" -srcfolder dist/dmg -ov -format UDZO SpineSpy.dmg

rm -rf dist/dmg
echo ""
echo "✅ Done! SpineSpy.dmg created"

# SpineSpy v1.1.0

Improved detection accuracy and camera-angle independence.

## What's New

- 🎯 **YOLO26s upgrade** - Upgraded phone detection model from YOLOv8n to YOLO26s (mAP 37.3 → 48.6), significantly improving small object detection accuracy
- 📐 **Posture calibration** - New calibration system captures your good-posture baseline so detection works regardless of camera angle
- 🔄 **Auto-calibrate on startup** - App automatically calibrates when launched
- 🎛️ **Calibrate menu item** - Re-calibrate anytime from the menubar menu with notification feedback

## Upgrading

```bash
pip install -r requirements.txt
```

The app will auto-download the new `yolo26s.pt` model (~19MB) on first launch.

## Installation

1. Download `SpineSpy.dmg`
2. Open the DMG and drag SpineSpy to Applications
3. Open SpineSpy from Applications
4. Grant camera permission when prompted

## Privacy

All processing happens locally on your device. No data is sent to external servers.

## Requirements

- macOS 10.15+
- Webcam

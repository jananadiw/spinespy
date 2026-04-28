# SpineSpy v1.1.1

AI-powered posture & focus monitor for your macOS menubar.

## Features

- 🦸 **Menubar app** - Shows posture status (🦸 good / 🧟 bad)
- 📸 **Periodic snapshots** - Camera opens briefly, then closes (not always-on)
- 🧘 **Posture detection** - Detects slouching and side tilting via MediaPipe
- 📐 **Posture calibration** - Saves your good-posture baseline for camera-angle independent checks
- 📱 **Improved phone detection** - Spots phone distractions using the upgraded YOLO26s model
- 🔔 **Smart alerts** - Only alerts after 5 consecutive bad snapshots
- ⏱️ **Configurable intervals** - 30s, 1min, 2min, or 5min
- ⏸️ **Pause/Resume** - Easy control from the menu
- 🧰 **Poetry startup** - Run with `poetry run start` or `./run.sh`

## What's Fixed

- Fixed Poetry startup by adding a proper package entrypoint for `poetry run start`
- Fixed `poetry install` package installation for the current project
- Fixed pytest collection so live camera demo scripts do not open the camera during test discovery
- Added clearer macOS camera permission guidance when snapshots or calibration cannot access the webcam
- Rebuilt the local Poetry environment after a corrupted OpenCV wheel caused Python crash reports in `cv2.abi3.so`

## Installation

1. Download `SpineSpy.dmg`
2. Open the DMG and drag SpineSpy to Applications
3. Open SpineSpy from Applications
4. Grant camera permission when prompted

## Developer Setup

```bash
poetry install
poetry run start
```

## Privacy

All processing happens locally on your device. No data is sent to external servers.

## Requirements

- macOS 10.15+
- Webcam

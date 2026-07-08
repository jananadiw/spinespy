# SpineSpy v1.1.1

AI-powered posture and focus monitoring for your macOS menubar.

## Features

- **Menubar status** - Shows posture status at a glance: good or bad.
- **Periodic snapshots** - Opens the camera briefly for each check, then closes it.
- **Posture detection** - Detects slouching and side tilting with MediaPipe.
- **Phone detection** - Spots phone distractions with the upgraded YOLO26s model.
- **Smart alerts** - Alerts only after 5 consecutive bad snapshots.
- **Voice reminders** - Plays a bundled posture reminder clip after repeated bad posture.
- **Sound toggle** - Lets you turn voice reminder clips on or off from Settings.
- **Configurable intervals** - Supports 30s, 1min, 2min, and 5min checks.
- **Pause and resume** - Lets you pause monitoring from the menubar.
- **Calibration** - Learns your good-posture baseline for camera-angle independent checks.

## Installation

1. Download `SpineSpy.dmg`.
2. Open the DMG and drag SpineSpy to Applications.
3. Open SpineSpy from Applications.
4. Grant camera permission when prompted.

## Privacy

All processing happens locally on your device. SpineSpy does not upload, store, or send camera images to external servers.

## Requirements

- macOS 10.15+
- Webcam

## Verification

`SpineSpy.dmg` is signed and notarized with Developer ID.

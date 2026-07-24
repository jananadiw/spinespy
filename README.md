# SpineSpy

> AI-powered posture & focus monitor that runs in your macOS menubar. Takes periodic snapshots to detect bad posture and phone distractions without keeping your camera always on.

[![Python](https://img.shields.io/github/languages/top/jananadiw/spinespy)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)
[![CI](https://github.com/jananadiw/spinespy/actions/workflows/ci.yml/badge.svg)](https://github.com/jananadiw/spinespy/actions/workflows/ci.yml)

If you want tiny local-first tools for healthier desk work, starring helps me know this is worth polishing.

## Demo
<img width="720" height="368" alt="SpineSpy floating posture pet reacting to repeated bad-posture checks" src="https://github.com/user-attachments/assets/d3683497-3486-4d6f-8821-7403d85c89f6" />

The demo shows the floating pet changing state and playing a reminder after repeated bad snapshots.

## Privacy

SpineSpy processes snapshots locally on your device. Camera frames stay in memory and are not uploaded or stored unless you explicitly choose **Save Snapshot**. Monitoring performs no network requests. Source builds download the two checksum-verified model files only when you run `./scripts/download_models.sh`.

## Features

- **Checks posture without a camera always-on feeling** - Opens the webcam briefly, analyzes a snapshot, then closes it
- **Learns your normal sitting position** - Calibrates against your own good-posture baseline instead of using a one-size-fits-all angle
- **Catches both slouching and leaning** - Flags forward slouching and side tilt with MediaPipe Pose
- **Nudges you when attention drifts** - Spots phone distractions with a lightweight MediaPipe object detector
- **Smart alerts** - Shows a notification and plays a posture reminder clip after repeated bad posture
- **Easy to keep out of the way** - Runs from the macOS menubar with a floating posture pet and speech bubble, pause, interval, calibration, and sound toggles
- **Makes camera use visible** - Shows opening, capturing, off, and local-processing states in the menubar
- **Remembers your preferences** - Persists the interval, sound setting, and calibration between launches

## Setup

```bash
# Clone the repo
git clone https://github.com/jananadiw/spinespy.git
cd spinespy

# Install dependencies
poetry install

# Download and checksum-verify the local AI models
./scripts/download_models.sh
```

## Usage

```bash
# Option 1: Using the run script
./run.sh

# Option 2: Poetry script
poetry run start

# Option 3: Direct Python module
poetry run python menubar_app.py
```

## Build

```bash
poetry install --with dev
./build_dmg.sh
```

The build requires Python 3.10 through 3.13 and the verified local model assets
`pose_landmarker.task` and `efficientdet_lite0.tflite`. It outputs
`dist/SpineSpy.app` and `SpineSpy.dmg`, and fails if the compressed DMG exceeds
200 MB.

Development builds use an ad hoc signature and are not notarized. Official
releases are signed, notarized, verified, and published locally; see
[docs/releasing.md](docs/releasing.md).

The app appears as a 🦸 icon in your menubar and shows a small floating posture pet with a state message above your windows. Right-click the menubar icon to:
- **✓ Monitoring** - Pause/resume monitoring
- **Camera: ...** - See exactly when the camera is opening, capturing, off, or processing locally
- **Interval** - Change snapshot frequency
- **Settings → Sound Clips** - Turn posture reminder clips on/off
- **Calibrate** - Capture your current good-posture baseline
- **Quit** - Exit the app

## How It Works

1. Every N minutes, the app briefly opens your camera and takes a snapshot
2. **MediaPipe Pose** analyzes the image for slouching or tilting relative to your calibrated baseline
3. A lightweight **MediaPipe EfficientDet-Lite0** model checks for phones in the frame
4. Camera closes immediately after capture; analysis continues locally with the camera off
5. Floating pet artwork, speech bubble, and menubar icon update: upright pet/🦸 (good) or curled pet/🧟 (bad posture)
6. After 5 consecutive bad snapshots → shows a notification and plays a random reminder clip if sound clips are enabled

## Configuration

Interval, sound, and calibration are saved locally in
`~/Library/Application Support/SpineSpy/settings.json`. No settings are synced or
uploaded.

Detection defaults remain in `menubar_app.py`:

```python
SLOUCH_THRESHOLD = 0.1   # forward lean sensitivity
TILT_THRESHOLD = 0.05    # side tilt sensitivity
BAD_STREAK_LIMIT = 5     # bad snapshots before alert
```

## Tech Stack

- **[OpenCV](https://opencv.org/)** - Camera snapshot capture
- **[MediaPipe](https://google.github.io/mediapipe/)** - Real-time pose estimation
- **[MediaPipe Object Detector](https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python)** - Lightweight on-device phone detection
- **[rumps](https://github.com/jaredks/rumps)** - macOS menubar application framework

## Requirements

- macOS (tested on macOS 10.15+)
- Python 3.10 through 3.13
- Webcam

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- MediaPipe for their excellent pose detection framework
- Google AI Edge for the MediaPipe pose and object-detection models
- The rumps library for making macOS menubar apps easy

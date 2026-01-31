# SpineSpy
[![Python](https://img.shields.io/github/languages/top/jananadiw/spinespy)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)](https://pypi.org/project/opencv-python/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-latest-orange.svg)](https://pypi.org/project/mediapipe/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple.svg)](https://pypi.org/project/ultralytics/)
[![rumps](https://img.shields.io/badge/rumps-latest-red.svg)](https://pypi.org/project/rumps/)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

> AI-powered posture & focus monitor that runs in your macOS menubar. Takes periodic snapshots to detect bad posture and phone distractions without keeping your camera always on.

## Features

- **Menubar App** - Lightweight icon that shows your posture status (🦸 good posture / 🧟 bad posture)
- **Periodic Snapshots** - Camera opens briefly every N minutes, then closes
- **Posture Detection** - Detects slouching forward and side tilting using MediaPipe Pose
- **Phone Detection** - Spots your phone using YOLOv8 object detection
- **Smart Alerts** - Only alerts after 5 consecutive bad snapshots (no false alarms!)
- **Configurable Interval** - Choose check frequency: 30s, 1min, 2min, or 5min
- **Pause/Resume** - Easily pause monitoring from the menu

## Setup

```bash
# Clone the repo
git clone https://github.com/jananadiw/spinespy.git
cd spinespy

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Option 1: Using the run script
./run.sh

# Option 2: Manual activation
source venv/bin/activate
python menubar_app.py

# Option 3: With Poetry (if you prefer)
poetry install
poetry run python menubar_app.py
```

The app appears as a 🦸 icon in your menubar. Right-click to:
- **✓ Monitoring** - Pause/resume monitoring
- **Interval** - Change snapshot frequency
- **Quit** - Exit the app

## How It Works

1. Every N minutes, the app briefly opens your camera and takes a snapshot
2. **MediaPipe Pose** analyzes the image for slouching or tilting
3. **YOLOv8** checks for phones in the frame
4. Camera closes immediately after analysis
5. Menubar icon updates: 🦸 (good) or 🧟 (bad posture)
6. After 5 consecutive bad snapshots → plays alert sound

## Configuration

Edit these values in `menubar_app.py`:

```python
SLOUCH_THRESHOLD = 0.1   # forward lean sensitivity
TILT_THRESHOLD = 0.05    # side tilt sensitivity
BAD_STREAK_LIMIT = 5     # bad snapshots before alert
```

## Tech Stack

- **[OpenCV](https://opencv.org/)** - Camera snapshot capture
- **[MediaPipe](https://google.github.io/mediapipe/)** - Real-time pose estimation
- **[YOLOv8](https://github.com/ultralytics/ultralytics)** (Ultralytics) - Object detection for phone spotting
- **[rumps](https://github.com/jaredks/rumps)** - macOS menubar application framework

## Requirements

- macOS (tested on macOS 10.15+)
- Python 3.8 or higher
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
- Ultralytics for YOLOv8
- The rumps library for making macOS menubar apps easy

---

**⚠️ Privacy Note:** SpineSpy processes all images locally on your device. No data is sent to external servers.

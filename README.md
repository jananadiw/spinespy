# SpineSpy

AI-powered posture & focus monitor that runs in your macOS menubar. Takes periodic snapshots to detect bad posture and phone distractions without keeping your camera always on.

## Features

- **Menubar App** - Lightweight icon that shows your posture status (🦸 hero / 🧟 zombie)
- **Periodic Snapshots** - Camera opens briefly every N minutes, then closes
- **Posture Detection** - Detects slouching forward and side tilting using MediaPipe Pose
- **Phone Detection** - Spots your phone using YOLOv8 object detection
- **Smart Alerts** - Only alerts after 5 consecutive bad snapshots (no false alarms!)
- **Configurable Interval** - Choose check frequency: 30s, 1min, 2min, or 5min
- **Pause/Resume** - Easily pause monitoring from the menu

## Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd postureguard

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python menubar_app.py
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

- OpenCV - Snapshot capture
- MediaPipe - Pose estimation
- YOLOv8 (Ultralytics) - Object detection
- rumps - macOS menubar app

## License

MIT

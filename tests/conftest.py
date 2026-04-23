"""Pytest configuration - mock heavy dependencies."""
import sys
from unittest.mock import MagicMock

# Mock rumps with real stub classes
mock_rumps = MagicMock()


class _StubApp:
    def __init__(self, title=None, **kwargs):
        self.title = title
        self.menu = []


class _StubMenuItem:
    def __init__(self, title=None, callback=None, **kwargs):
        self.title = title
        self.callback = callback
        self._items = []

    def add(self, item):
        self._items.append(item)


class _StubTimer:
    def __init__(self, callback=None, interval=None, **kwargs):
        self.callback = callback
        self.interval = interval

    def start(self):
        pass

    def stop(self):
        pass


mock_rumps.App = _StubApp
mock_rumps.MenuItem = _StubMenuItem
mock_rumps.Timer = _StubTimer
sys.modules["rumps"] = mock_rumps

# Mock cv2
mock_cv2 = MagicMock()
sys.modules["cv2"] = mock_cv2

# Mock mediapipe with new API structure
mock_mp = MagicMock()
mock_mp.Image = MagicMock
mock_mp.ImageFormat.SRGB = MagicMock()

# Mock mediapipe.tasks.python
mock_python = MagicMock()
mock_python.BaseOptions = MagicMock
sys.modules["mediapipe.tasks"] = MagicMock()
sys.modules["mediapipe.tasks.python"] = mock_python

# Mock mediapipe.tasks.python.vision
mock_vision = MagicMock()
mock_vision.PoseLandmarkerOptions = MagicMock
mock_vision.PoseLandmarker.create_from_options = MagicMock()
sys.modules["mediapipe.tasks.python.vision"] = mock_vision

sys.modules["mediapipe"] = mock_mp

# Mock ultralytics
mock_yolo = MagicMock()
sys.modules["ultralytics"] = mock_yolo

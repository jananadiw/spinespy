"""Pytest configuration - mock heavy dependencies."""
import sys
from unittest.mock import MagicMock

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

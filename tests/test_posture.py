"""Unit tests for posture detection."""

from unittest.mock import MagicMock

from menubar_app import SLOUCH_THRESHOLD, TILT_THRESHOLD, check_posture


def make_landmark(x=0, y=0, z=0):
    """Create a mock landmark with x, y, z coordinates."""
    lm = MagicMock()
    lm.x = x
    lm.y = y
    lm.z = z
    return lm


def make_landmarks(nose_z=0, shoulder_z=0, left_y=0.5, right_y=0.5):
    """Create mock landmarks dict for testing."""
    landmarks = {}
    landmarks[0] = make_landmark(z=nose_z)  # NOSE = 0
    landmarks[11] = make_landmark(y=left_y, z=shoulder_z)  # LEFT_SHOULDER = 11
    landmarks[12] = make_landmark(y=right_y, z=shoulder_z)  # RIGHT_SHOULDER = 12
    return landmarks


class TestCheckPosture:
    def test_good_posture(self):
        landmarks = make_landmarks(nose_z=0, shoulder_z=0)
        is_bad, reason = check_posture(landmarks)
        assert is_bad is False
        assert reason is None

    def test_slouching_forward(self):
        # Nose closer to camera (smaller z) than shoulders = slouching
        landmarks = make_landmarks(nose_z=0, shoulder_z=SLOUCH_THRESHOLD + 0.05)
        is_bad, reason = check_posture(landmarks)
        assert is_bad is True
        assert reason == "Slouching"

    def test_tilting_sideways(self):
        # Shoulders at different heights = tilting
        landmarks = make_landmarks(left_y=0.5, right_y=0.5 + TILT_THRESHOLD + 0.02)
        is_bad, reason = check_posture(landmarks)
        assert is_bad is True
        assert reason == "Tilting"

    def test_slouch_threshold_boundary(self):
        # Exactly at threshold should trigger
        landmarks = make_landmarks(nose_z=0, shoulder_z=SLOUCH_THRESHOLD)
        is_bad, _ = check_posture(landmarks)
        assert is_bad is True

    def test_tilt_threshold_boundary(self):
        # Exactly at threshold should trigger
        landmarks = make_landmarks(left_y=0.5, right_y=0.5 + TILT_THRESHOLD)
        is_bad, _ = check_posture(landmarks)
        assert is_bad is True

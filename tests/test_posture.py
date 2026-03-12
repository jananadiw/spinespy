"""Unit tests for posture detection."""

from unittest.mock import MagicMock

import menubar_app
from menubar_app import SLOUCH_THRESHOLD, TILT_THRESHOLD, check_posture, _severity_label


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
    landmarks[0] = make_landmark(z=nose_z)
    landmarks[11] = make_landmark(y=left_y, z=shoulder_z)
    landmarks[12] = make_landmark(y=right_y, z=shoulder_z)
    return landmarks


def setup_function():
    menubar_app.baseline_lean = 0.0
    menubar_app.baseline_tilt = 0.0
    menubar_app.effective_slouch_threshold = SLOUCH_THRESHOLD
    menubar_app.effective_tilt_threshold = TILT_THRESHOLD


class TestCheckPosture:
    def test_good_posture(self):
        landmarks = make_landmarks(nose_z=0, shoulder_z=0)
        is_bad, reason = check_posture(landmarks)
        assert is_bad is False
        assert reason is None

    def test_slouching_forward(self):
        landmarks = make_landmarks(nose_z=0, shoulder_z=SLOUCH_THRESHOLD + 0.05)
        is_bad, reason = check_posture(landmarks)
        assert is_bad is True
        assert "Slouching" in reason

    def test_tilting_sideways(self):
        landmarks = make_landmarks(left_y=0.5, right_y=0.5 + TILT_THRESHOLD + 0.02)
        is_bad, reason = check_posture(landmarks)
        assert is_bad is True
        assert "Tilting" in reason

    def test_slouch_threshold_boundary(self):
        landmarks = make_landmarks(nose_z=0, shoulder_z=SLOUCH_THRESHOLD)
        is_bad, _ = check_posture(landmarks)
        assert is_bad is True

    def test_tilt_threshold_boundary(self):
        landmarks = make_landmarks(left_y=0.5, right_y=0.5 + TILT_THRESHOLD)
        is_bad, _ = check_posture(landmarks)
        assert is_bad is True


class TestSeverityLabel:
    def test_mild(self):
        assert _severity_label(0.12, 0.1) == "mild"

    def test_moderate(self):
        assert _severity_label(0.2, 0.1) == "moderate"

    def test_severe(self):
        assert _severity_label(0.3, 0.1) == "severe"

    def test_exactly_at_threshold(self):
        assert _severity_label(0.1, 0.1) == "mild"


class TestSeverityInReason:
    def test_slouch_includes_severity(self):
        landmarks = make_landmarks(nose_z=0, shoulder_z=SLOUCH_THRESHOLD)
        _, reason = check_posture(landmarks)
        assert "Slouching (mild)" == reason

    def test_severe_slouch(self):
        landmarks = make_landmarks(nose_z=0, shoulder_z=SLOUCH_THRESHOLD * 3)
        _, reason = check_posture(landmarks)
        assert "Slouching (severe)" == reason


class TestAdaptiveThresholds:
    def test_wider_threshold_prevents_false_positive(self):
        menubar_app.effective_slouch_threshold = 0.2
        landmarks = make_landmarks(nose_z=0, shoulder_z=0.15)
        is_bad, _ = check_posture(landmarks)
        assert is_bad is False

    def test_wider_threshold_still_catches_bad_posture(self):
        menubar_app.effective_slouch_threshold = 0.2
        landmarks = make_landmarks(nose_z=0, shoulder_z=0.25)
        is_bad, reason = check_posture(landmarks)
        assert is_bad is True
        assert "Slouching" in reason

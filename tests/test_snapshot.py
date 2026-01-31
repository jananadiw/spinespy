"""Integration tests for snapshot flow."""

from unittest.mock import MagicMock, patch

import numpy as np


class TestTakeSnapshot:
    @patch("menubar_app.cv2.VideoCapture")
    @patch("menubar_app.detect_phone")
    @patch("menubar_app.pose_detector")
    def test_good_posture_no_phone(self, mock_pose_detector, mock_detect_phone, mock_cap_class):
        from menubar_app import take_snapshot

        # Mock camera
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap_class.return_value = mock_cap

        # Mock pose - no landmarks detected
        mock_pose_detector.detect.return_value = MagicMock(pose_landmarks=None)
        mock_detect_phone.return_value = False

        is_bad, reason = take_snapshot()
        assert is_bad is False
        assert reason == "Good posture"
        mock_cap.release.assert_called_once()

    @patch("menubar_app.cv2.VideoCapture")
    @patch("menubar_app.detect_phone")
    @patch("menubar_app.pose_detector")
    def test_phone_detected(self, mock_pose_detector, mock_detect_phone, mock_cap_class):
        from menubar_app import take_snapshot

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap_class.return_value = mock_cap

        mock_pose_detector.detect.return_value = MagicMock(pose_landmarks=None)
        mock_detect_phone.return_value = True

        is_bad, reason = take_snapshot()
        assert is_bad is True
        assert reason == "Phone detected"

    @patch("menubar_app.cv2.VideoCapture")
    def test_camera_error(self, mock_cap_class):
        from menubar_app import take_snapshot

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_class.return_value = mock_cap

        is_bad, reason = take_snapshot()
        assert is_bad is None
        assert reason == "Camera error"

    @patch("menubar_app.cv2.VideoCapture")
    def test_capture_failed(self, mock_cap_class):
        from menubar_app import take_snapshot

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_cap_class.return_value = mock_cap

        is_bad, reason = take_snapshot()
        assert is_bad is None
        assert reason == "Capture failed"


class TestPostureGuardApp:
    @patch("menubar_app.take_snapshot")
    @patch("menubar_app.play_alert")
    def test_bad_streak_triggers_alert(self, mock_alert, mock_snapshot):
        from menubar_app import BAD_STREAK_LIMIT, PostureGuardApp

        mock_snapshot.return_value = (True, "Slouching")

        with patch("menubar_app.rumps.Timer"):
            app = PostureGuardApp()
            app.timer = MagicMock()

            # Simulate bad snapshots up to limit
            for i in range(BAD_STREAK_LIMIT):
                app.check_posture(None)

            mock_alert.assert_called_once()
            assert app.bad_streak == 0  # Reset after alert

    @patch("menubar_app.take_snapshot")
    @patch("menubar_app.play_alert")
    def test_good_posture_resets_streak(self, mock_alert, mock_snapshot):
        from menubar_app import PostureGuardApp

        with patch("menubar_app.rumps.Timer"):
            app = PostureGuardApp()
            app.timer = MagicMock()
            app.bad_streak = 3

            mock_snapshot.return_value = (False, "Good posture")
            app.check_posture(None)

            assert app.bad_streak == 0
            mock_alert.assert_not_called()

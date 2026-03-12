"""Integration tests for snapshot flow."""

from collections import Counter
from unittest.mock import MagicMock, patch, call

import numpy as np


class TestTakeSnapshot:
    @patch("menubar_app.cv2.VideoCapture")
    @patch("menubar_app.detect_phone")
    @patch("menubar_app.pose_detector")
    def test_good_posture_no_phone(self, mock_pose_detector, mock_detect_phone, mock_cap_class):
        from menubar_app import take_snapshot

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap_class.return_value = mock_cap

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

    @patch("menubar_app.cv2.VideoCapture")
    @patch("menubar_app.detect_phone")
    @patch("menubar_app.check_posture")
    @patch("menubar_app.pose_detector")
    def test_majority_voting_bad(self, mock_pose_detector, mock_check, mock_detect_phone, mock_cap_class):
        from menubar_app import take_snapshot

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap_class.return_value = mock_cap

        mock_landmarks = MagicMock()
        mock_pose_detector.detect.return_value = MagicMock(pose_landmarks=[mock_landmarks])

        mock_check.side_effect = [
            (True, "Slouching (mild)"),
            (True, "Slouching (mild)"),
            (False, None),
        ]
        mock_detect_phone.return_value = False

        is_bad, reason = take_snapshot()
        assert is_bad is True
        assert "Slouching" in reason

    @patch("menubar_app.cv2.VideoCapture")
    @patch("menubar_app.detect_phone")
    @patch("menubar_app.check_posture")
    @patch("menubar_app.pose_detector")
    def test_majority_voting_good(self, mock_pose_detector, mock_check, mock_detect_phone, mock_cap_class):
        from menubar_app import take_snapshot

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap_class.return_value = mock_cap

        mock_landmarks = MagicMock()
        mock_pose_detector.detect.return_value = MagicMock(pose_landmarks=[mock_landmarks])

        mock_check.side_effect = [
            (True, "Slouching (mild)"),
            (False, None),
            (False, None),
        ]
        mock_detect_phone.return_value = False

        is_bad, reason = take_snapshot()
        assert is_bad is False
        assert reason == "Good posture"


class TestPostureGuardApp:
    def _make_app(self):
        from menubar_app import PostureGuardApp
        with patch("menubar_app.threading.Thread"):
            app = PostureGuardApp()
            app.timer = MagicMock()
        return app

    @patch("menubar_app.take_snapshot")
    @patch("menubar_app.play_alert")
    @patch("menubar_app.rumps.notification")
    def test_bad_streak_triggers_alert_and_notification(self, mock_notification, mock_alert, mock_snapshot):
        from menubar_app import BAD_STREAK_LIMIT

        mock_snapshot.return_value = (True, "Slouching (moderate)")
        app = self._make_app()

        for i in range(BAD_STREAK_LIMIT):
            app.check_posture(None)

        mock_alert.assert_called_once()
        assert app.bad_streak == 0
        assert app.bad_reasons == []
        mock_notification.assert_any_call(
            "SpineSpy",
            "Posture Alert",
            f"Slouching (moderate) detected {BAD_STREAK_LIMIT}/{BAD_STREAK_LIMIT} checks. Sit up straight!",
        )

    @patch("menubar_app.take_snapshot")
    @patch("menubar_app.play_alert")
    def test_good_posture_resets_streak(self, mock_alert, mock_snapshot):
        app = self._make_app()
        app.bad_streak = 3
        app.bad_reasons = ["Slouching (mild)"] * 3

        mock_snapshot.return_value = (False, "Good posture")
        app.check_posture(None)

        assert app.bad_streak == 0
        assert app.bad_reasons == []
        mock_alert.assert_not_called()

    @patch("menubar_app.take_snapshot")
    def test_calibrating_skips_check(self, mock_snapshot):
        app = self._make_app()
        app.calibrating = True

        app.check_posture(None)
        mock_snapshot.assert_not_called()

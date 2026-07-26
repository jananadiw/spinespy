"""Integration tests for snapshot flow."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from spinespy.settings import AppSettings, CalibrationSettings


class _PetPanelStub:
    def __init__(self):
        self.state = None
        self.state_changes = []

    def set_state(self, state):
        self.state = state
        self.state_changes.append(state)

    def show(self):
        pass


class _ImmediateFuture:
    def __init__(self, callback, *args):
        try:
            self.value = callback(*args)
            self.error = None
        except Exception as error:
            self.value = None
            self.error = error

    def result(self):
        if self.error is not None:
            raise self.error
        return self.value

    def add_done_callback(self, callback):
        callback(self)


class _ImmediateExecutor:
    def __init__(self):
        self.shutdown_calls = []

    def submit(self, callback, *args):
        return _ImmediateFuture(callback, *args)

    def shutdown(self, **kwargs):
        self.shutdown_calls.append(kwargs)


class TestOpenCamera:
    @patch("menubar_app.cv2.VideoCapture")
    def test_uses_avfoundation_default_on_macos(self, mock_cap_class):
        import menubar_app

        menubar_app.cv2.CAP_AVFOUNDATION = 1200

        with patch("menubar_app.sys.platform", "darwin"):
            menubar_app.open_camera()

        mock_cap_class.assert_called_once_with(0, 1200)


class TestDetectPhone:
    @patch("menubar_app.get_phone_detections")
    def test_detects_cell_phone_from_mediapipe_result(self, mock_detections):
        from menubar_app import detect_phone

        category = MagicMock(category_name="cell phone", score=0.82)
        detection = MagicMock(categories=[category])
        mock_detections.return_value = [detection]

        assert detect_phone(np.zeros((480, 640, 3), dtype=np.uint8)) is True

    @patch("menubar_app.get_phone_detections")
    def test_returns_false_without_cell_phone(self, mock_detections):
        from menubar_app import detect_phone

        mock_detections.return_value = []

        assert detect_phone(np.zeros((480, 640, 3), dtype=np.uint8)) is False


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
    @patch("menubar_app.pose_detector")
    def test_camera_state_reports_exact_capture_window(
        self, mock_pose_detector, mock_detect_phone, mock_cap_class
    ):
        from menubar_app import take_snapshot

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap_class.return_value = mock_cap
        mock_pose_detector.detect.return_value = MagicMock(pose_landmarks=None)
        mock_detect_phone.return_value = False
        states = []

        take_snapshot(camera_state_callback=states.append)

        assert states == ["opening", "on", "off"]
        mock_cap.release.assert_called_once()

    @patch("menubar_app.cv2.VideoCapture")
    def test_camera_state_returns_to_off_after_open_error(self, mock_cap_class):
        from menubar_app import take_snapshot

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_class.return_value = mock_cap
        states = []

        take_snapshot(camera_state_callback=states.append)

        assert states == ["opening", "off"]

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


class TestSaveCameraFrame:
    @patch("menubar_app.cv2.imwrite", return_value=True)
    @patch("menubar_app.cv2.VideoCapture")
    def test_saves_one_frame_without_inference(self, mock_cap_class, mock_imwrite):
        from menubar_app import save_camera_frame

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, frame)
        mock_cap_class.return_value = mock_cap

        result = save_camera_frame("/tmp/snapshot.jpg")

        assert result.succeeded is True
        assert result.value == "/tmp/snapshot.jpg"
        mock_imwrite.assert_called_once()
        mock_cap.release.assert_called_once()

    @patch("menubar_app.cv2.imwrite", return_value=False)
    @patch("menubar_app.cv2.VideoCapture")
    def test_reports_failed_write(self, mock_cap_class, mock_imwrite):
        from menubar_app import save_camera_frame

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (
            True,
            np.zeros((480, 640, 3), dtype=np.uint8),
        )
        mock_cap_class.return_value = mock_cap

        result = save_camera_frame("/tmp/snapshot.jpg")

        assert result.succeeded is False
        assert "/tmp/snapshot.jpg" in result.message


class TestOperationCoordinator:
    def test_rejects_overlap_and_discards_invalidated_result(self):
        from menubar_app import OperationCoordinator

        coordinator = OperationCoordinator()
        token = coordinator.reserve()

        assert token is not None
        assert coordinator.reserve() is None
        coordinator.invalidate_result()
        assert coordinator.finish(token) is False
        assert coordinator.reserve() is not None

    def test_shutdown_rejects_new_work(self):
        from menubar_app import OperationCoordinator

        coordinator = OperationCoordinator()
        coordinator.begin_shutdown()

        assert coordinator.reserve() is None


class TestPostureGuardApp:
    def _make_app(self, settings=None):
        from menubar_app import PostureGuardApp

        settings_store = MagicMock()
        settings_store.load.return_value = settings or AppSettings()
        with patch("menubar_app.FloatingPetPanel", _PetPanelStub):
            app = PostureGuardApp(
                settings_store=settings_store,
                executor=_ImmediateExecutor(),
            )
            app.timer = MagicMock()
            app._dispatch_main = lambda callback, *args: callback(*args)
        return app

    def test_initializes_floating_pet_panel(self):
        from menubar_app import ICON_GOOD

        app = self._make_app()

        assert app.pet_panel.state == "good"
        assert app.pet_panel.state_changes == ["good"]
        assert app.title == ICON_GOOD

    def test_pet_image_assets_are_bundled(self):
        import menubar_app

        app_root = Path(menubar_app.__file__).resolve().parent

        for relative_path in menubar_app.PET_IMAGE_FILES.values():
            assert (app_root / relative_path).is_file()

    def test_pet_states_have_messages(self):
        import menubar_app

        assert set(menubar_app.PET_MESSAGES) == {"good", "bad", "checking", "calibrating", "paused"}
        assert menubar_app.PET_MESSAGES["good"] == "Sitting nice and straight!"
        assert menubar_app.PET_MESSAGES["bad"] == "You're being a shrimp, my friend."
        assert "Camera" in menubar_app.PET_MESSAGES["checking"]

    @patch("menubar_app.take_snapshot")
    @patch("menubar_app.play_alert")
    @patch("menubar_app.rumps.notification")
    def test_bad_streak_triggers_sound_clip(self, mock_notification, mock_alert, mock_snapshot):
        from menubar_app import BAD_STREAK_LIMIT

        mock_snapshot.return_value = (True, "Slouching (moderate)")
        app = self._make_app()

        for _ in range(BAD_STREAK_LIMIT):
            app.check_posture(None)

        mock_alert.assert_called_once_with(True)
        assert app.bad_streak == 0
        assert app.bad_reasons == []
        assert app.pet_panel.state == "bad"
        mock_notification.assert_not_called()

    @patch("menubar_app.take_snapshot")
    @patch("menubar_app.play_alert")
    def test_bad_posture_updates_floating_pet(self, mock_alert, mock_snapshot):
        from menubar_app import ICON_BAD

        mock_snapshot.return_value = (True, "Slouching (moderate)")
        app = self._make_app()

        app.check_posture(None)

        assert app.pet_panel.state == "bad"
        assert app.title == ICON_BAD
        mock_alert.assert_not_called()

    @patch("menubar_app.take_snapshot")
    @patch("menubar_app.play_alert")
    def test_sound_clip_toggle_disables_bad_posture_audio(self, mock_alert, mock_snapshot):
        from menubar_app import BAD_STREAK_LIMIT

        mock_snapshot.return_value = (True, "Slouching (moderate)")
        app = self._make_app()

        app.toggle_sound_clips(app.sound_clips_item)
        assert app.sound_clips_enabled is False
        assert app.sound_clips_item.title == "Sound Clips (off)"

        for _ in range(BAD_STREAK_LIMIT):
            app.check_posture(None)

        mock_alert.assert_called_once_with(False)
        assert app.bad_streak == 0
        assert app.bad_reasons == []

    @patch("menubar_app.take_snapshot")
    @patch("menubar_app.play_alert")
    def test_check_posture_uses_default_camera(self, mock_alert, mock_snapshot):
        mock_snapshot.return_value = (False, "Good posture")
        app = self._make_app()

        app.check_posture(None)

        assert mock_snapshot.call_count == 1
        assert callable(mock_snapshot.call_args.kwargs["camera_state_callback"])
        assert mock_snapshot.call_args.kwargs["cancel_event"] is not None
        mock_alert.assert_not_called()

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
        assert app.pet_panel.state == "good"

    @patch("menubar_app.take_snapshot")
    def test_calibrating_skips_check(self, mock_snapshot):
        from menubar_app import Operation

        app = self._make_app()
        app._operations.reserve()
        app.active_operation = Operation.CALIBRATING

        app.check_posture(None)
        mock_snapshot.assert_not_called()

    def test_pause_updates_floating_pet(self):
        app = self._make_app()

        app.toggle_monitoring(app.monitoring_item)
        assert app.pet_panel.state == "paused"

        app.toggle_monitoring(app.monitoring_item)
        assert app.pet_panel.state == "good"

    def test_loads_persisted_preferences_and_calibration(self):
        import menubar_app

        app = self._make_app(
            AppSettings(
                interval=120,
                sound_clips_enabled=False,
                calibration=CalibrationSettings(
                    baseline_lean=0.11,
                    baseline_tilt=0.02,
                    slouch_threshold=0.14,
                    tilt_threshold=0.07,
                ),
            )
        )

        assert app.interval == 120
        assert app.sound_clips_enabled is False
        assert app.has_saved_calibration is True
        assert app.sound_clips_item.title == "Sound Clips (off)"
        assert app.interval_items[120].title == "✓ 2 minutes"
        assert menubar_app.baseline_lean == 0.11
        assert menubar_app.effective_tilt_threshold == 0.07

    def test_camera_status_is_visible_during_capture_and_processing(self):
        app = self._make_app()
        token = app._operations.reserve()

        app._camera_state_changed(token, "opening")
        assert app.camera_status_item.title == "Camera: Opening…"
        assert app.pet_panel.state == "checking"

        app._camera_state_changed(token, "on")
        assert app.camera_status_item.title == "Camera: On • Capturing"

        app._camera_state_changed(token, "off")
        assert app.camera_status_item.title == "Camera: Off • Processing locally"

        app._operations.finish(token)
        app.camera_status_item.title = "Camera: Off"
        assert app.camera_status_item.title == "Camera: Off"

    @patch("menubar_app.rumps.notification")
    @patch("menubar_app.save_camera_frame", side_effect=RuntimeError("write failed"))
    def test_save_snapshot_reports_worker_failure(self, mock_save, mock_notification):
        app = self._make_app()
        app.set_posture_state("bad")
        app._choose_snapshot_path = lambda: "/tmp/snapshot.jpg"

        app.save_snapshot(None)

        assert app.pet_panel.state == "bad"
        assert app.camera_status_item.title == "Camera: Off"
        mock_notification.assert_called_once_with(
            "SpineSpy", "Snapshot failed", "write failed"
        )

    @patch("menubar_app.save_camera_frame")
    def test_save_panel_cancel_does_not_open_camera(self, mock_save):
        app = self._make_app()
        app._choose_snapshot_path = lambda: None

        app.save_snapshot(None)

        mock_save.assert_not_called()

    @patch("menubar_app.take_snapshot", return_value=(True, "Slouching (mild)"))
    def test_pause_discards_active_result(self, mock_snapshot):
        from menubar_app import Operation, OperationResult

        app = self._make_app()
        token = app._operations.reserve()
        app.active_operation = Operation.MONITORING
        app.toggle_monitoring(app.monitoring_item)

        app._finish_operation(
            token,
            app._complete_monitoring,
            OperationResult(True, value=(True, "Slouching (mild)")),
        )

        assert app.paused is True
        assert app.bad_streak == 0
        assert app.pet_panel.state == "paused"

    @patch("menubar_app.close_detectors")
    @patch("menubar_app.rumps.quit_application")
    def test_quit_shuts_down_executor_and_detectors(self, mock_quit, mock_close):
        app = self._make_app()

        app.quit_app(None)

        assert app._executor.shutdown_calls == [
            {"wait": True, "cancel_futures": True}
        ]
        mock_close.assert_called_once()
        mock_quit.assert_called_once()

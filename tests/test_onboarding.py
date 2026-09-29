"""First-launch lifecycle, persistence failures, and camera gating."""

import json
from unittest.mock import MagicMock, patch

import pytest

from spinespy.settings import AppSettings, CalibrationSettings, SettingsStore


@pytest.fixture
def launch(tmp_path):
    from menubar_app import PostureGuardApp

    store = SettingsStore(tmp_path / "settings.json")
    with (
        patch("menubar_app.FloatingPetPanel"),
        patch("menubar_app.WelcomeWindow"),
        patch("menubar_app.discover_cameras", return_value=()),
        patch("menubar_app.rumps.Timer"),
        patch("menubar_app.PostureGuardApp._request_startup_calibration"),
        patch("menubar_app.baseline_lean", 0.0),
        patch("menubar_app.baseline_tilt", 0.0),
        patch("menubar_app.effective_slouch_threshold", 0.1),
        patch("menubar_app.effective_tilt_threshold", 0.05),
    ):
        def make_app(settings=None):
            if settings is not None:
                store.save(settings)
            return PostureGuardApp(settings_store=store, executor=MagicMock())

        yield make_app


def test_first_launch_waits_for_answers_before_camera_or_pet(launch):
    app = launch()

    app._startup()

    app.welcome_window.show.assert_called_once_with(
        primary_need=None, interval=600, completed=False,
    )
    app.pet_panel.show.assert_not_called()
    app._request_startup_calibration.assert_not_called()
    assert app.timer is None
    assert app.next_capture_at is None
    assert app.monitoring_item.title == "Finish Setup…"
    assert not app.settings_store.path.exists()


@pytest.mark.parametrize("interval", [600, 1200, 1800, 3600])
def test_completion_saves_before_starting_and_skips_welcome_after_restart(launch, interval):
    app = launch()
    app._startup()

    with patch("menubar_app.time.time", return_value=100):
        assert app._complete_onboarding("movement", interval) is True

    saved = app.settings_store.load()
    assert saved.onboarding_completed is True
    assert saved.primary_need == "movement"
    assert saved.interval == interval
    assert app.next_capture_at == 100 + interval
    app.welcome_window.hide.assert_called_once()
    app.pet_panel.show.assert_called_once()
    app._request_startup_calibration.assert_called_once()
    app.timer.start.assert_called_once()

    returning = launch()
    with patch.object(returning, "show_welcome") as show:
        returning._startup()
    show.assert_not_called()
    assert returning.interval == interval
    assert returning.primary_need == "movement"


def test_saved_calibration_is_kept_through_onboarding(launch):
    calibration = CalibrationSettings(0.1, 0.02, 0.15, 0.08)
    app = launch(AppSettings(calibration=calibration, camera_unique_id="my-camera"))

    app._complete_onboarding("pain", 1800)

    saved = app.settings_store.load()
    assert saved.calibration == calibration
    assert saved.camera_unique_id == "my-camera"
    app._request_startup_calibration.assert_not_called()


def test_failed_save_keeps_setup_incomplete_and_retryable(launch):
    app = launch()
    app._startup()
    with patch.object(app.settings_store, "save", side_effect=OSError("Disk full")):
        assert app._complete_onboarding("posture", 900) is False

    assert app.onboarding_completed is False
    assert app.primary_need is None
    assert app.interval == 600
    assert app.timer is None
    app.welcome_window.hide.assert_not_called()
    app.pet_panel.show.assert_not_called()
    app._request_startup_calibration.assert_not_called()
    assert app._complete_onboarding("posture", 900) is True


def test_manual_camera_and_timer_actions_cannot_bypass_setup(launch):
    app = launch()
    with (
        patch("menubar_app.camera_authorization_status") as status,
        patch("menubar_app.request_camera_access") as permission,
        patch.object(app, "_choose_snapshot_path") as save_dialog,
        patch.object(app, "_start_posture_check") as capture,
    ):
        app.check_posture(None)
        app.run_calibration(None)
        app.save_snapshot(None)
        app.toggle_monitoring(app.monitoring_item)
        app.set_interval(900)
        app._start_monitoring_timer()

    status.assert_not_called()
    permission.assert_not_called()
    capture.assert_not_called()
    save_dialog.assert_not_called()
    assert app.timer is None
    assert app.next_capture_at is None
    assert app.interval == 600


def test_closing_unfinished_welcome_quits_without_marking_complete(launch):
    app = launch()
    with patch("menubar_app.rumps.quit_application") as quit_app:
        app._welcome_closed()

    quit_app.assert_called_once()
    assert app.onboarding_completed is False
    assert not app.settings_store.path.exists()


def test_editing_answers_while_paused_does_not_restart_camera(launch):
    app = launch(AppSettings(primary_need="posture", onboarding_completed=True))
    app._startup()
    app.toggle_monitoring(app.monitoring_item)
    app.timer.reset_mock()

    app.show_welcome()
    assert app._complete_onboarding("pain", 7200) is True

    assert app.paused is True
    assert app.next_capture_at is None
    app.timer.start.assert_not_called()
    assert app.settings_store.load().primary_need == "pain"
    assert app.settings_store.load().interval == 7200
    with patch.object(app, "quit_app") as quit_app:
        app._welcome_closed()
    quit_app.assert_not_called()


def test_other_settings_changes_preserve_answers(launch):
    app = launch(AppSettings(primary_need="movement", onboarding_completed=True))

    app.toggle_sound_clips(app.sound_clips_item)
    app.set_interval(900)

    saved = app.settings_store.load()
    assert saved.primary_need == "movement"
    assert saved.onboarding_completed is True
    assert saved.interval == 900
    assert saved.sound_clips_enabled is False


def test_sub_ten_minute_intervals_cannot_be_selected(launch):
    app = launch(AppSettings(primary_need="posture", onboarding_completed=True))

    for interval in (30, 60, 120, 300):
        app.set_interval(interval)

    assert app.interval == 600
    assert tuple(app.interval_items) == (600, 1200, 1800, 3600)


def test_legacy_interval_is_preserved_until_a_new_preset_is_chosen(launch):
    app = launch(AppSettings(interval=900, primary_need="posture", onboarding_completed=True))

    assert app.interval_menu.title == "Interval (15 minutes)"
    assert app.interval == 900
    app.set_interval(1200)
    assert app.interval_items[1200].title == "✓ 20 minutes"
    assert app.interval_menu.title == "Interval"


def test_immediate_rumps_timer_tick_waits_until_selected_deadline(launch):
    app = launch(AppSettings(interval=900, primary_need="posture", onboarding_completed=True))
    with patch("menubar_app.time.time", return_value=100):
        app._startup()

    with patch.object(app, "check_posture") as capture:
        for now in (100, 101, 999):
            with patch("menubar_app.time.time", return_value=now):
                app._scheduled_posture_check(None)
        capture.assert_not_called()
        with patch("menubar_app.time.time", return_value=1000):
            app._scheduled_posture_check(None)
        capture.assert_called_once_with(None)

        # Small run-loop delays must not cause every other repeating tick to skip.
        app.next_capture_at = 1900.05
        with patch("menubar_app.time.time", return_value=1900):
            app._scheduled_posture_check(None)
        assert capture.call_count == 2


def test_pause_before_startup_handles_missing_timer(launch):
    app = launch(AppSettings(primary_need="posture", onboarding_completed=True))
    assert app.timer is None

    app.toggle_monitoring(app.monitoring_item)

    assert app.paused is True
    assert app.next_capture_at is None
    assert app.monitoring_item.title == "Resume Monitoring"
    app.toggle_monitoring(app.monitoring_item)
    app.timer.start.assert_called_once()


def test_existing_calibrated_install_starts_without_welcome_and_can_dismiss_settings(launch):
    initial = launch()
    initial.settings_store.path.write_text(json.dumps({
        "version": 2,
        "interval": 120,
        "camera_unique_id": "my-camera",
        "calibration": {
            "baseline_lean": 0.1, "baseline_tilt": 0.02,
            "slouch_threshold": 0.15, "tilt_threshold": 0.08,
        },
    }))
    app = launch()
    app._startup()

    assert app.welcome_window is None
    assert app.primary_need == "posture"
    assert app.interval == 600
    assert app.camera_unique_id == "my-camera"
    app.pet_panel.show.assert_called_once()
    app.timer.start.assert_called_once()
    app._request_startup_calibration.assert_not_called()
    app.show_welcome()
    app.welcome_window.show.assert_called_once_with(
        primary_need="posture", interval=600, completed=True,
    )
    with patch.object(app, "quit_app") as quit_app:
        app._welcome_closed()
    quit_app.assert_not_called()

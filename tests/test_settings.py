"""Tests for local SpineSpy settings persistence."""

import json

import pytest

from spinespy.settings import AppSettings, CalibrationSettings, SettingsStore


def test_settings_round_trip(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    expected = AppSettings(
        interval=900,
        sound_clips_enabled=False,
        camera_unique_id="FaceTime-HD-stable-id",
        primary_need="movement",
        onboarding_completed=True,
        calibration=CalibrationSettings(
            baseline_lean=0.12,
            baseline_tilt=0.03,
            slouch_threshold=0.15,
            tilt_threshold=0.08,
        ),
    )

    store.save(expected)

    assert store.load() == expected


def test_missing_settings_use_defaults(tmp_path):
    store = SettingsStore(tmp_path / "missing.json")

    assert store.load() == AppSettings()


def test_corrupt_settings_use_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not-json", encoding="utf-8")

    assert SettingsStore(path).load() == AppSettings()


def test_invalid_values_fall_back_without_discarding_valid_values(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        '{"interval": 999, "sound_clips_enabled": false, "calibration": {}}',
        encoding="utf-8",
    )

    assert SettingsStore(path).load() == AppSettings(sound_clips_enabled=False)


def test_invalid_camera_identifier_is_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        '{"camera_unique_id": "", "interval": 900}',
        encoding="utf-8",
    )

    assert SettingsStore(path).load() == AppSettings(interval=900)


@pytest.mark.parametrize("seconds", [30, 60, 120, 300])
def test_legacy_intervals_migrate_to_ten_minutes_without_losing_preferences(tmp_path, seconds):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({
        "version": 2,
        "interval": seconds,
        "sound_clips_enabled": False,
        "camera_unique_id": "saved-camera",
        "calibration": {
            "baseline_lean": 0.12,
            "baseline_tilt": 0.03,
            "slouch_threshold": 0.15,
            "tilt_threshold": 0.08,
        },
    }))

    settings = SettingsStore(path).load()

    assert settings.interval == 600
    assert settings.sound_clips_enabled is False
    assert settings.camera_unique_id == "saved-camera"
    assert settings.calibration == CalibrationSettings(0.12, 0.03, 0.15, 0.08)
    assert settings.onboarding_completed is False


@pytest.mark.parametrize("interval", [600, 900, 1200, 1800, 3600, 7200])
@pytest.mark.parametrize("need", ["posture", "movement", "pain"])
def test_all_welcome_answers_survive_restart(tmp_path, interval, need):
    path = tmp_path / "settings.json"
    expected = AppSettings(interval=interval, primary_need=need, onboarding_completed=True)

    SettingsStore(path).save(expected)

    assert SettingsStore(path).load() == expected


@pytest.mark.parametrize("need", [None, [], {}, "unknown"])
def test_invalid_need_requires_setup_again(tmp_path, need):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"primary_need": need, "onboarding_completed": True}))

    assert SettingsStore(path).load().onboarding_completed is False


@pytest.mark.parametrize("completed", ["true", 1, [], None])
def test_only_boolean_completion_skips_welcome(tmp_path, completed):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"primary_need": "posture", "onboarding_completed": completed}))

    assert SettingsStore(path).load().onboarding_completed is False


@pytest.mark.parametrize("interval", [0, 540, 601, 2700, 86400, 900.0, "900", True, None])
def test_unsupported_interval_falls_back_to_ten_minutes(tmp_path, interval):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"interval": interval}))

    assert SettingsStore(path).load().interval == 600

"""Tests for local SpineSpy settings persistence."""

from spinespy.settings import AppSettings, CalibrationSettings, SettingsStore


def test_settings_round_trip(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    expected = AppSettings(
        interval=120,
        sound_clips_enabled=False,
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

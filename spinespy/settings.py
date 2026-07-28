"""Persistent, local-only settings for SpineSpy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any


VALID_INTERVALS = (30, 60, 120, 300)


@dataclass(frozen=True)
class CalibrationSettings:
    baseline_lean: float
    baseline_tilt: float
    slouch_threshold: float
    tilt_threshold: float


@dataclass(frozen=True)
class AppSettings:
    interval: int = 60
    sound_clips_enabled: bool = True
    camera_unique_id: str | None = None
    calibration: CalibrationSettings | None = None


def default_settings_path() -> Path:
    return Path.home() / "Library" / "Application Support" / "SpineSpy" / "settings.json"


class SettingsStore:
    """Read and atomically write SpineSpy settings as a small JSON file."""

    def __init__(self, path: Path | None = None):
        self.path = path or default_settings_path()

    def load(self) -> AppSettings:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return AppSettings()

        if not isinstance(payload, dict):
            return AppSettings()

        interval = payload.get("interval", 60)
        if interval not in VALID_INTERVALS:
            interval = 60

        sound_enabled = payload.get("sound_clips_enabled", True)
        if not isinstance(sound_enabled, bool):
            sound_enabled = True

        camera_unique_id = payload.get("camera_unique_id")
        if (
            not isinstance(camera_unique_id, str)
            or not camera_unique_id
            or len(camera_unique_id) > 512
        ):
            camera_unique_id = None

        calibration = self._load_calibration(payload.get("calibration"))
        return AppSettings(
            interval=interval,
            sound_clips_enabled=sound_enabled,
            camera_unique_id=camera_unique_id,
            calibration=calibration,
        )

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".tmp")
        payload = {
            "version": 2,
            "interval": settings.interval,
            "sound_clips_enabled": settings.sound_clips_enabled,
            "camera_unique_id": settings.camera_unique_id,
            "calibration": asdict(settings.calibration) if settings.calibration else None,
        }
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, self.path)

    @staticmethod
    def _load_calibration(value: Any) -> CalibrationSettings | None:
        if not isinstance(value, dict):
            return None

        keys = (
            "baseline_lean",
            "baseline_tilt",
            "slouch_threshold",
            "tilt_threshold",
        )
        if not all(isinstance(value.get(key), (int, float)) for key in keys):
            return None
        if value["slouch_threshold"] <= 0 or value["tilt_threshold"] <= 0:
            return None

        return CalibrationSettings(
            baseline_lean=float(value["baseline_lean"]),
            baseline_tilt=float(value["baseline_tilt"]),
            slouch_threshold=float(value["slouch_threshold"]),
            tilt_threshold=float(value["tilt_threshold"]),
        )

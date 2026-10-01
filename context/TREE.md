# Tree

Start here. Load a node only when the task needs it.

## Runtime
- `menubar_app.py` — menubar app, floating pet, snapshot/calibration, MediaPipe detectors
- `spinespy/camera.py` — AVFoundation discovery, selection, authorization
- `spinespy/settings.py` — local JSON preferences and calibration
- `spinespy/onboarding.py` — native welcome window
- `spinespy/cli.py` — `poetry run start` and live phone test

## Tests
- `tests/test_snapshot.py` — capture, operations, app wiring
- `tests/test_onboarding.py` — welcome gating and persistence
- `tests/test_camera.py` — camera selection
- `tests/test_settings.py` — settings schema and migration
- `tests/test_posture.py` — lean/tilt thresholds
- `tests/test_release_scripts.py` — DMG, signing, notarization policy

## Build and release
- `build_dmg.sh` — PyInstaller app + DMG; bundles `assets/`
- `scripts/download_models.sh` — checksum-verified pose and phone models
- `scripts/release_local.sh` / `scripts/verify_macos_app.sh`
- `docs/releasing.md`

## Bundled assets
- `assets/pets/posture-{good,bad}.png` — floating pet
- `assets/menubar/` — menu bar icons
- `assets/audio/` — reminder clips
- `assets/branding/SpineSpyIcon.png`

# SpineSpy 1.2.2

This release focuses on easier installation, verifiable privacy, and clearer
camera behavior.

## Adoption and trust improvements

- Replaces the PyTorch/Ultralytics phone-detection runtime with a lightweight
  MediaPipe EfficientDet-Lite0 model while preserving phone detection.
- Enforces a 200 MB maximum compressed DMG size in local and CI builds.
- Adds pull-request CI for the complete test suite and a packaging smoke test.
- Makes model downloads explicit and verifies pinned SHA-256 checksums.
- Persists the monitoring interval, sound preference, and posture calibration
  locally between launches.
- Shows when the camera is opening, actively capturing, off, and processing the
  captured frame locally.

## Release verification

Local builds are ad hoc signed and are not notarized. Tagged GitHub releases
are published only if Developer ID signing, hardened-runtime signing, Apple
notarization, stapling, and Gatekeeper verification all succeed. See
`docs/releasing.md` for the required secrets and verification commands.

## Privacy

Monitoring uses bundled on-device models and makes no network requests. Camera
frames remain in memory and are discarded after analysis unless the user
explicitly selects **Save Snapshot**.

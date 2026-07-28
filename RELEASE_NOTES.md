# SpineSpy 1.2.3

This release makes camera use predictable, keeps monitoring local, and
strengthens the complete macOS release pipeline.

## Camera and runtime reliability

- Defaults to the Mac's built-in camera instead of silently choosing an iPhone
  Continuity Camera or another external device.
- Adds a Camera menu with stable device selection and remembers an explicitly
  selected camera.
- Invalidates calibration after switching cameras so measurements are not
  applied to a different viewpoint.
- Requests camera permission on the AppKit thread and serializes capture,
  calibration, snapshot, and inference work.
- Shows the selected camera and its opening, active, off, and local-processing
  states.
- Fixes packaged startup when the Camera submenu has not yet created its native
  menu object.

## Privacy

- Pins a MediaPipe build without the native Clearcut metrics uploader.
- Rejects release bundles if the uploader symbol reappears.
- Keeps posture and phone inference on-device and releases the camera
  immediately after each capture.

## Release engineering

- Builds an Apple Silicon app for macOS 15 with a pinned local toolchain.
- Verifies every Mach-O file, entitlement, hardened-runtime signature, Team ID,
  timestamp, and bundle version before packaging.
- Adds a branded drag-to-Applications DMG, a 200 MB size gate, notarization-log
  policy, post-staple hashing, and downloaded-draft verification.
- Keeps Developer ID and notarization credentials in the maintainer's local
  Keychain.

## Release verification

Official releases are built and published locally only after Developer ID
signing, hardened-runtime signing, Apple notarization, stapling, and Gatekeeper
verification all succeed. Release credentials remain in the maintainer's local
Keychain. See `docs/releasing.md` for the release and verification commands.

Camera frames remain in memory and are discarded after analysis unless the user
explicitly selects **Save Snapshot**.

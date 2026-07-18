# Decisions

## 2026-07-18: Use MediaPipe for phone detection

- Decision: Replace the PyTorch/Ultralytics runtime with MediaPipe EfficientDet-Lite0 and keep both models explicit, checksum-verified build assets.
- Reason: Preserve phone detection while keeping the macOS download small and eliminating silent runtime downloads.
- Impact: Source builds run `scripts/download_models.sh`; packaged monitoring is fully local and the DMG is capped at 200 MB.
- Revisit: If a smaller Core ML detector materially improves accuracy or energy use.

## 2026-07-18: Fail closed for official macOS releases

- Decision: Publish tagged releases only after Developer ID signing, notarization, stapling, and Gatekeeper verification succeed.
- Reason: An ad hoc signature must never be represented to users as a notarized release.
- Impact: Release CI requires Apple credentials; local builds remain clearly labeled as ad hoc.
- Revisit: If release authentication moves from Apple ID credentials to App Store Connect API keys.

## 2026-07-18: Persist user preferences and calibration locally

- Decision: Store interval, sound preference, and calibration in the user's Application Support directory, while resetting paused state on launch.
- Reason: Repeated setup hurts adoption, while silently preserving a paused monitor can mislead users.
- Impact: Returning users keep their configuration and avoid unnecessary startup calibration.
- Revisit: If desk-profile switching requires multiple named calibrations.

## 2026-07-18: Show exact camera lifecycle state

- Decision: Expose opening, capturing, off, and local-processing states in the menubar and floating pet.
- Reason: A camera-based privacy tool should make actual camera use legible rather than only promising it in documentation.
- Impact: Users can distinguish the brief capture window from subsequent on-device inference.
- Revisit: If macOS provides a reliable system camera-usage observer that should replace callbacks.

## 2026-07-08: Add pet speech bubble messages

- Decision: Show a short rounded speech bubble beside the floating pet for each posture state.
- Reason: The pet should feel more expressive without interrupting the user with modal dialogs.
- Impact: Good, bad, paused, and calibrating states now update both artwork and text.
- Revisit: If messages should depend on specific bad-posture reasons instead of one bad-state line.

## 2026-07-08: Use artwork assets for the floating pet

- Decision: Replace the floating pet emoji placeholders with bundled transparent posture artwork.
- Reason: The pet panel should show the user's good and bad posture drawings instead of generic symbols.
- Impact: Good, paused, and calibrating states use the upright pet image; bad posture uses the curled pet image.
- Revisit: If the pet needs animated states or separate paused/calibrating artwork.

## 2026-07-08: Use floating pet panel for posture state

- Decision: Show posture state in a small always-on-top AppKit panel while keeping the menubar icon as a fallback.
- Reason: The pet should stay visible above normal app windows and later support richer personalized cues.
- Impact: Posture, calibration, and pause state changes now route through a shared pet/status helper.
- Revisit: If the panel needs richer controls or animation.

## 2026-06-08: Build DMG through Poetry

- Decision: Run PyInstaller through Poetry and bundle every required inference model. The original YOLO asset was superseded by the 2026-07-18 MediaPipe decision.
- Reason: Poetry owns the supported Python 3.10-3.13 environment, and explicit model assets keep builds reproducible.
- Impact: `./build_dmg.sh` now requires `poetry install --with dev` and fails early on unsupported Python or missing assets.
- Revisit: If the project moves to a different packager or stops using Poetry.

## 2026-06-03: Use system default camera

- Decision: Keep camera handling automatic and open the system default camera through AVFoundation on macOS.
- Reason: The app should avoid extra camera configuration before posture tracking starts.
- Impact: Calibration, snapshots, and manual captures all use the same default camera path.
- Revisit: If users still see macOS selecting an unwanted Continuity Camera.

## 2026-05-31: Use sound clips for bad-posture alerts

- Decision: Replace the bad-posture notification with a random bundled reminder clip and a menubar Settings toggle.
- Reason: Posture alerts should be audible prompts without requiring notification banners.
- Impact: Startup and calibration notifications remain, while bad-posture streaks play clips only when enabled.
- Revisit: Notification fallback; the sound preference became persistent on 2026-07-18.

## 2026-05-31: Bound Python support to 3.10-3.13

- Decision: Declare support for Python >=3.10,<3.14.
- Reason: The supported application and packaging dependency set is tested on this range.
- Impact: Poetry resolves one reproducible environment, and README requirements match packaging metadata.
- Revisit: When the full dependency set and packaged app are verified on Python 3.14.

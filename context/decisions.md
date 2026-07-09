# Decisions

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

- Decision: Run PyInstaller through Poetry and bundle `yolo26s.pt`.
- Reason: The app loads `yolo26s.pt`, and Poetry already owns the supported Python 3.10-3.13 environment.
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
- Revisit: If users need persistent sound preferences or notification fallback.

## 2026-05-31: Bound Python support to 3.10-3.13

- Decision: Declare support for Python >=3.10,<3.14.
- Reason: The patched PyTorch 2.8 dependency line pulls Triton 3.4, which does not declare Python 3.14 support.
- Impact: Poetry can resolve the secure PyTorch lockfile, and README requirements now match packaging metadata.
- Revisit: When PyTorch/Triton support Python 3.14 in the selected dependency line.

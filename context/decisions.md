# Decisions

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

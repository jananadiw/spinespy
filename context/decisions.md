# Decisions

## 2026-07-18: Use MediaPipe for phone detection

- Decision: Use MediaPipe EfficientDet-Lite0 and keep all inference models explicit, checksum-verified build assets.
- Reason: Preserve phone detection while keeping the macOS download small and preventing silent runtime downloads.
- Impact: Monitoring stays local; source builds download verified models, and packaged builds must include them.
- Revisit: If a smaller Core ML detector materially improves accuracy or energy use.

## 2026-07-25: Keep official macOS releases local and staged

- Decision: Build exact tags with a pinned arm64 toolchain, sign and notarize locally, verify a downloaded draft on clean macOS 15, then publish it unchanged.
- Reason: Protect local credentials while proving Gatekeeper and users receive the exact tested artifact.
- Impact: `scripts/release_local.sh stage` prepares the draft; `publish` requires the clean-machine gate. CI remains ad hoc.
- Revisit: When additional maintainers or unattended releases justify secured release automation.

## 2026-07-18: Persist preferences and calibration locally

- Decision: Store interval, sound preference, and calibration in Application Support, but reset paused state on launch.
- Reason: Preserve useful setup without allowing a silently paused monitor to mislead users.
- Impact: Returning users keep their configuration and normally avoid recalibration.
- Revisit: If desk-profile switching requires multiple named calibrations.

## 2026-07-25: Serialize camera work and show its lifecycle

- Decision: Reserve camera operations through one worker and token, while exposing opening, capturing, off, and local-processing states.
- Reason: Prevent overlapping camera work and stale UI while letting users distinguish camera access from local inference.
- Impact: Pause and quit invalidate results; AppKit updates return to the main thread; Save Snapshot uses a separate one-frame path.
- Revisit: If macOS provides a reliable system camera-usage observer that should replace callbacks.

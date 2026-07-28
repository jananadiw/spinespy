# Decisions

## 2026-07-27: Pin the local-only vision stack

- Decision: Pin MediaPipe 0.10.33 and OpenCV 4.11.0.86; keep inference models explicit, checksum-verified build assets.
- Reason: MediaPipe 0.10.33 removes the vulnerable Protobuf dependency and lacks the metrics uploader found in later wheels.
- Impact: Source support is Python 3.10–3.12; release verification rejects the uploader symbol.
- Revisit: When a supported MediaPipe release offers a documented telemetry opt-out, or Core ML replaces it.

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

- Decision: Serialize camera work, request permission on the main thread, select by AVFoundation ID, and default only to built-in hardware.
- Reason: Prevent overlap, stale UI, worker-thread permission failures, and unintended Continuity Camera capture.
- Impact: Users see camera state/name, can persist an explicit external camera, and must recalibrate after switching.
- Revisit: If macOS provides a reliable system camera-usage observer that should replace callbacks.

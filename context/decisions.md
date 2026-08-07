# Decisions

## 2026-07-27: Pin the local-only vision stack

- Decision: Pin MediaPipe 0.10.33 and OpenCV 4.11.0.86; keep inference models explicit, checksum-verified build assets.
- Reason: MediaPipe 0.10.33 removes the vulnerable Protobuf dependency and lacks the metrics uploader found in later wheels.
- Impact: Source support is Python 3.10–3.12; release verification rejects the uploader symbol.
- Revisit: When a supported MediaPipe release offers a documented telemetry opt-out, or Core ML replaces it.

## 2026-08-06: Automate staged macOS releases

- Decision: A version bump merged to `main` tags, signs, notarizes, and stages a draft on an ephemeral GitHub macOS runner; publication remains gated by clean-Mac validation.
- Reason: Remove local release toil without weakening the physical camera, Gatekeeper, and exact-artifact checks.
- Impact: Signing secrets live in the protected `release-signing` environment; `release-publish` gates publication of the unchanged draft.
- Revisit: If GitHub-hosted signing is no longer trusted or clean-device testing can be automated safely.

## 2026-07-18: Persist preferences and calibration locally

- Decision: Store interval, sound preference, and calibration in Application Support, but reset paused state on launch.
- Reason: Preserve useful setup without allowing a silently paused monitor to mislead users.
- Impact: Returning users keep their configuration and normally avoid recalibration.
- Revisit: If desk-profile switching requires multiple named calibrations.

## 2026-08-05: Serialize camera work and make capture timing explicit

- Decision: Serialize camera work, request permission on the main thread, select by AVFoundation ID, show the next capture time, stop scheduling while paused, and show 📷 only during camera access.
- Reason: Prevent overlap, stale UI, worker-thread permission failures, unintended Continuity Camera capture, and ambiguous periodic access.
- Impact: Users can predict and pause captures, distinguish camera access from local processing, persist an explicit external camera, and recalibrate after switching.
- Revisit: If macOS provides a reliable camera-usage observer or scheduler API that should replace callbacks and local deadlines.

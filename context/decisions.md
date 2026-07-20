# Decisions

## 2026-07-18: Use MediaPipe for phone detection

- Decision: Use MediaPipe EfficientDet-Lite0 and keep all inference models explicit, checksum-verified build assets.
- Reason: Preserve phone detection while keeping the macOS download small and preventing silent runtime downloads.
- Impact: Monitoring stays local; source builds download verified models, and packaged builds must include them.
- Revisit: If a smaller Core ML detector materially improves accuracy or energy use.

## 2026-07-18: Fail closed for official macOS releases

- Decision: Publish tagged releases only after Developer ID signing, notarization, stapling, and Gatekeeper verification succeed.
- Reason: An ad hoc signature must never be presented as a notarized release.
- Impact: Release CI requires Apple credentials; local builds remain explicitly ad hoc.
- Revisit: If release authentication moves to App Store Connect API keys.

## 2026-07-18: Persist preferences and calibration locally

- Decision: Store interval, sound preference, and calibration in Application Support, but reset paused state on launch.
- Reason: Preserve useful setup without allowing a silently paused monitor to mislead users.
- Impact: Returning users keep their configuration and normally avoid recalibration.
- Revisit: If desk-profile switching requires multiple named calibrations.

## 2026-07-18: Show exact camera lifecycle state

- Decision: Expose opening, capturing, off, and local-processing states in the menubar and floating pet.
- Reason: Users should be able to distinguish camera access from on-device inference.
- Impact: Camera use is visible during the brief capture window and explicitly off during processing.
- Revisit: If macOS provides a reliable system camera-usage observer that should replace callbacks.

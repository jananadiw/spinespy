# Decisions

## 2026-07-18: Use MediaPipe for phone detection

- Decision: Use MediaPipe EfficientDet-Lite0 and keep all inference models explicit, checksum-verified build assets.
- Reason: Preserve phone detection while keeping the macOS download small and preventing silent runtime downloads.
- Impact: Monitoring stays local; source builds download verified models, and packaged builds must include them.
- Revisit: If a smaller Core ML detector materially improves accuracy or energy use.

## 2026-07-20: Keep official macOS release credentials local

- Decision: Sign, notarize, verify, and publish official releases from the maintainer's Mac; keep ordinary CI free of release credentials.
- Reason: A sole maintainer can protect the Developer ID private key and Apple credentials locally without weakening Gatekeeper verification.
- Impact: Official releases use `scripts/release_local.sh`; development and CI builds remain explicitly ad hoc.
- Revisit: When additional maintainers or unattended releases justify secured release automation.

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

# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately:

1. **Do not** open a public issue
2. Use GitHub's private vulnerability reporting for this repository
3. Include details about the vulnerability and steps to reproduce

We will respond within 48 hours and work with you to understand and address the issue.

## Security Considerations

SpineSpy processes all camera frames locally on your device. Monitoring does not make network requests or send data to external servers. The app requires:

- **Camera access**: For posture monitoring snapshots
- **No monitoring network access**: All AI processing is done locally with bundled models

In the packaged app, camera frames are held in memory only and released after
analysis. The **Save Snapshot** debugging command is the sole image-writing path
and runs only after an explicit user action.

Source checkouts do not silently download executable or model content at
runtime. Contributors explicitly run `./scripts/download_models.sh`, which
downloads two public Google AI Edge model files and verifies pinned SHA-256
checksums before using them. Official release builds bundle those verified
models and require no model downloads after installation.

Tagged releases are created only after Developer ID signing, hardened-runtime
signing, Apple notarization, stapling, and Gatekeeper verification succeed. A
local `./build_dmg.sh` build uses an ad hoc signature and prints that it is not
notarized.

## Updates

Security updates will be released as soon as possible after a vulnerability is confirmed.

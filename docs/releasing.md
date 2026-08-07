# Releasing SpineSpy

Official SpineSpy releases are built, signed, notarized, and staged by GitHub
Actions. Publishing remains a separate approval after the exact draft DMG passes
the clean-Mac checklist.

## Release environments and secrets

Create these GitHub environments in the repository settings:

- `release-signing` holds the signing and Apple notarization secrets. It does
  not require a reviewer, so staging starts as soon as a release version reaches
  `main`.
- `release-publish` should require a maintainer reviewer. Approval means the
  exact draft asset passed the clean-macOS test below.

Add these secrets to `release-signing`:

- `MACOS_DEVELOPER_ID_P12_BASE64`: base64-encoded Developer ID Application
  certificate and private key exported as a password-protected `.p12`.
- `MACOS_DEVELOPER_ID_P12_PASSWORD`: password for that `.p12`.
- `APPLE_NOTARY_KEY_P8_BASE64`: base64-encoded App Store Connect API key.
- `APPLE_NOTARY_KEY_ID`: API key ID.
- `APPLE_NOTARY_ISSUER_ID`: API issuer ID.

Encode binary credentials without adding line breaks:

```bash
base64 -i DeveloperIDApplication.p12 | tr -d '\n'
base64 -i AuthKey_KEYID.p8 | tr -d '\n'
```

The workflow decodes these only on an ephemeral GitHub-hosted runner, imports
the certificate into a temporary Keychain, and removes both after the job.

## Start a release

Prepare a PR that:

- increments the version in `pyproject.toml`;
- starts `RELEASE_NOTES.md` with `# SpineSpy X.Y.Z`; and
- passes the normal pull-request checks.

When that PR is merged into `main`, `.github/workflows/release.yml` detects the
version increase. It creates `vX.Y.Z` at the merge commit and then:

1. Installs the pinned arm64 release toolchain on `macos-15`.
2. Imports the protected credentials into a temporary Keychain.
3. Installs locked dependencies and checksum-verified models.
4. Runs the complete test suite.
5. Builds and signs the arm64 app and DMG.
6. Audits the app and rejects invalid signatures or entitlements.
7. Notarizes, staples, and validates the DMG.
8. Creates a draft GitHub release with its checksum and release evidence.
9. Downloads the draft asset and verifies the downloaded bytes.

An ordinary PR that does not increase the version does not create a release.
If staging fails after the tag is created, rerun the failed workflow. It accepts
an existing tag only when that tag points to the same merge commit and refuses
to replace an existing GitHub release.

To stage the current version without another version bump, use **Actions →
Stage macOS release → Run workflow**. This is intended for the first automated
release or recovery; normal releases should come from versioned PRs.

The known `pose_landmarker.task/pose_detector.tflite` archive-unpacking warning
is allowed by stable severity, path, and message fields. Any new warning fails
the release for manual review.

## Local fallback

The same release script can stage an existing tag from an Apple Silicon Mac
with Python 3.11, Poetry 2.3.1, create-dmg 1.3.0, a Developer ID identity, and a
`spinespy-notary` Keychain profile:

```bash
./scripts/release_local.sh stage v1.2.3
```

## Clean macOS 15 gate

Test the exact DMG downloaded from the draft release with a fresh macOS 15 user
and fresh camera-permission state:

- Drag SpineSpy into `/Applications` and launch it through Gatekeeper.
- Deny camera access, confirm the guidance, then grant access and retry.
- Calibrate, monitor, pause during a check, and save and cancel a snapshot.
- Quit during camera work and relaunch with saved settings.
- Disconnect networking and confirm the installed app still works.
- Confirm no source checkout, Python installation, Poetry environment, or
  external model file is required.

Do not replace the draft asset after this test. Replacing it requires a complete
new signing, notarization, stapling, hashing, and validation cycle.

## Publish the unchanged draft

Only after the clean-machine gate passes:

1. Open **Actions → Publish macOS release → Run workflow**.
2. Enter the draft tag.
3. Check the clean-macOS validation confirmation.
4. Approve the `release-publish` environment when prompted.

The publish job downloads and verifies the draft DMG again before making the
release public. The equivalent local fallback is:

```bash
CLEAN_MACOS15_VALIDATED=yes ./scripts/release_local.sh publish v1.2.3
```

## Development build

Development builds remain ad hoc signed and cannot be represented as notarized:

```bash
poetry install --with dev
brew install create-dmg
./scripts/download_models.sh
./build_dmg.sh
codesign --verify --deep --strict --verbose=2 dist/SpineSpy.app
```

After downloading an official release, verify its notarization ticket and
Gatekeeper assessment:

```bash
xcrun stapler validate SpineSpy.dmg
spctl --assess --type open --context context:primary-signature --verbose=2 SpineSpy.dmg
```

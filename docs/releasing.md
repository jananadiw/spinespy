# Releasing SpineSpy

Official SpineSpy releases are built, signed, notarized, and published from the
maintainer's Mac. The Developer ID private key and Apple credentials remain in
the local Keychain and are never stored in GitHub.

## One-time notarization setup

Install a valid Developer ID Application identity in Keychain Access, then save
the Apple notarization credentials in a local Keychain profile:

```bash
xcrun notarytool store-credentials "spinespy-notary"
```

Enter the Apple ID, team ID `FWFFM858T2`, and app-specific password at the
prompts so the password is not recorded in shell history.

## Required local toolchain

Official releases require a native Apple Silicon environment, not Rosetta:

```bash
python --version       # Python 3.11.x
poetry --version       # Poetry 2.3.1
create-dmg --version   # create-dmg 1.3.0
```

The build targets arm64 and macOS 15. It fails when the interpreter,
architecture, tool versions, bundle metadata, nested signatures, entitlements,
or compressed-DMG size do not match release policy.

## Stage an existing tag

Prepare the release commit first. Its tag, package version, bundle version, and
first release-note heading must all describe the same version. Push the tag,
then stage it:

```bash
./scripts/release_local.sh stage v1.2.3
```

The stage command:

1. Resolves the exact remote tag into a detached temporary worktree.
2. Installs the locked dependencies and checksum-verified models.
3. Runs the complete test suite.
4. Builds the arm64 app with a macOS 15 deployment target.
5. Signs collected native code and signs the completed app bundle last.
6. Audits every bundled Mach-O and rejects `get-task-allow`.
7. Creates and signs the branded DMG.
8. Submits it with `notarytool`, saves the submission and log, and rejects any
   unknown notarization issue.
9. Staples and validates the DMG before calculating its SHA-256 checksum.
10. Creates a draft GitHub release, uploads the evidence, downloads the DMG
    again, and verifies that the downloaded bytes match.

The known `pose_landmarker.task/pose_detector.tflite` archive-unpacking warning
is allowed by stable severity, path, and message fields. Any new warning fails
the release for manual review.

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

```bash
CLEAN_MACOS15_VALIDATED=yes \
  ./scripts/release_local.sh publish v1.2.3
```

The publish command downloads and verifies the draft DMG again before making
the release public. Set `NOTARY_PROFILE`, `CODESIGN_IDENTITY`, or
`EXPECTED_TEAM_ID` only when the documented local defaults are not intended.

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

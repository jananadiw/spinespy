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

## Publish an existing tag

The release script checks out the exact tag in a temporary worktree, installs
the locked dependencies, downloads the checksum-verified models, runs the test
suite, and builds a DMG under 200 MB. It signs the app and DMG with the local
Developer ID identity, submits the DMG to Apple, staples and verifies the
notarization ticket, runs Gatekeeper assessment, and creates the GitHub release.

```bash
./scripts/release_local.sh v1.2.2
```

Set `NOTARY_PROFILE` or `CODESIGN_IDENTITY` only when the local defaults are not
the intended credentials.

## Development build

Development builds remain ad hoc signed and cannot be represented as notarized:

```bash
poetry install --with dev
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

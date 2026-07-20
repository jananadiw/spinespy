# Releasing SpineSpy

Official SpineSpy releases are built by `.github/workflows/release.yml`. The
workflow deliberately fails before building when any signing or notarization
credential is missing.

## Required GitHub Actions secrets

- `MACOS_CERTIFICATE_P12`: base64-encoded Developer ID Application certificate
  and private key in PKCS#12 format
- `MACOS_CERTIFICATE_PASSWORD`: password used when exporting that PKCS#12 file
- `KEYCHAIN_PASSWORD`: throwaway password for the temporary CI keychain
- `APPLE_ID`: Apple account used for notarization
- `APPLE_APP_PASSWORD`: app-specific password for that Apple account
- `APPLE_TEAM_ID`: Apple Developer team identifier

The workflow imports the certificate into a temporary keychain, installs the
locked dependencies, verifies both model checksums, runs the tests, builds a DMG
under 200 MB, signs the app and DMG, submits the DMG to Apple, staples the
ticket, and verifies it with `stapler`, `codesign`, and Gatekeeper before it can
create a GitHub release.

## Local verification

Local builds are intentionally ad hoc signed and cannot be represented as
notarized:

```bash
poetry install --with dev
./scripts/download_models.sh
./build_dmg.sh
codesign --verify --deep --strict --verbose=2 dist/SpineSpy.app
```

After downloading an official release, verify the notarization ticket and
Gatekeeper assessment:

```bash
xcrun stapler validate SpineSpy.dmg
spctl --assess --type open --context context:primary-signature --verbose=2 SpineSpy.dmg
```

#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

EXPECTED_PYTHON_MINOR="${EXPECTED_PYTHON_MINOR:-3.11}"
EXPECTED_POETRY_VERSION="${EXPECTED_POETRY_VERSION:-2.3.1}"
EXPECTED_CREATE_DMG_VERSION="${EXPECTED_CREATE_DMG_VERSION:-1.3.0}"
EXPECTED_TEAM_ID="${EXPECTED_TEAM_ID:-FWFFM858T2}"
MINIMUM_SYSTEM_VERSION="${MINIMUM_SYSTEM_VERSION:-15.0}"
CODESIGN_IDENTITY="${CODESIGN_IDENTITY:--}"
MAX_DMG_SIZE_MB="${MAX_DMG_SIZE_MB:-200}"

[[ "$(uname -m)" == "arm64" ]] || {
    echo "Official SpineSpy builds require a native Apple Silicon host." >&2
    exit 1
}
[[ "$(sysctl -in sysctl.proc_translated 2>/dev/null || echo 0)" != "1" ]] || {
    echo "Rosetta builds are not supported." >&2
    exit 1
}
[[ "$(poetry --version)" == "Poetry (version ${EXPECTED_POETRY_VERSION})" ]] || {
    echo "Poetry ${EXPECTED_POETRY_VERSION} is required." >&2
    exit 1
}
[[ "$(poetry run python -c 'import platform; print(platform.machine())')" == "arm64" ]] || {
    echo "The Poetry environment must use native arm64 Python." >&2
    exit 1
}
[[ "$(poetry run python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" == "$EXPECTED_PYTHON_MINOR" ]] || {
    echo "Python ${EXPECTED_PYTHON_MINOR} is required for reproducible builds." >&2
    exit 1
}
command -v create-dmg >/dev/null || {
    echo "create-dmg ${EXPECTED_CREATE_DMG_VERSION} is required. Install it with Homebrew." >&2
    exit 1
}
create-dmg --version 2>&1 | grep -Fq "$EXPECTED_CREATE_DMG_VERSION" || {
    echo "create-dmg ${EXPECTED_CREATE_DMG_VERSION} is required." >&2
    exit 1
}

export MACOSX_DEPLOYMENT_TARGET="$MINIMUM_SYSTEM_VERSION"

poetry run python - <<'PY'
from importlib.metadata import version
import pathlib

expected_versions = {
    "mediapipe": "0.10.21",
    "opencv-contrib-python": "4.11.0.86",
}
unexpected = {
    package: (version(package), expected)
    for package, expected in expected_versions.items()
    if version(package) != expected
}
if unexpected:
    details = ", ".join(
        f"{package}={installed} (expected {expected})"
        for package, (installed, expected) in unexpected.items()
    )
    raise SystemExit(f"Unexpected vision dependency version(s): {details}")

required = (
    "pose_landmarker.task",
    "efficientdet_lite0.tflite",
    "assets",
    "assets/branding/SpineSpyIcon.png",
    "assets/dmg/background.tiff",
    "entitlements.plist",
)
missing = [path for path in required if not pathlib.Path(path).exists()]
if missing:
    raise SystemExit(f"Missing required build asset(s): {', '.join(missing)}")
PY

APP_VERSION="$(
poetry run python - <<'PY'
import pathlib
import tomllib

with pathlib.Path("pyproject.toml").open("rb") as file:
    print(tomllib.load(file)["tool"]["poetry"]["version"])
PY
)"

rm -rf build dist SpineSpy.dmg
mkdir -p build/icon.iconset build/spec dist

ICON_SOURCE="assets/branding/SpineSpyIcon.png"
for SIZE in 16 32 128 256 512; do
    sips -z "$SIZE" "$SIZE" "$ICON_SOURCE" \
        --out "build/icon.iconset/icon_${SIZE}x${SIZE}.png" >/dev/null
    DOUBLE_SIZE=$((SIZE * 2))
    sips -z "$DOUBLE_SIZE" "$DOUBLE_SIZE" "$ICON_SOURCE" \
        --out "build/icon.iconset/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done
iconutil -c icns build/icon.iconset -o build/SpineSpy.icns

PYINSTALLER_ARGS=(
    --name SpineSpy
    --windowed
    --clean
    --noconfirm
    --specpath build/spec
    --target-architecture arm64
    --icon "$ROOT_DIR/build/SpineSpy.icns"
    --add-data "$ROOT_DIR/pose_landmarker.task:."
    --add-data "$ROOT_DIR/efficientdet_lite0.tflite:."
    --add-data "$ROOT_DIR/assets:assets"
    --hidden-import rumps
    --hidden-import cv2
    --hidden-import mediapipe
    --hidden-import mediapipe.tasks.c
    --hidden-import AppKit
    --collect-all mediapipe
    --exclude-module jax
    --exclude-module jaxlib
    --exclude-module scipy
    --exclude-module sentencepiece
    --osx-bundle-identifier com.jananadiw.spinespy
)
if [[ "$CODESIGN_IDENTITY" != "-" ]]; then
    PYINSTALLER_ARGS+=(--codesign-identity "$CODESIGN_IDENTITY")
fi
poetry run pyinstaller "${PYINSTALLER_ARGS[@]}" menubar_app.py

PLIST="dist/SpineSpy.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string 'SpineSpy uses the camera briefly to check posture and processes frames on this Mac.'" "$PLIST" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Set :NSCameraUsageDescription 'SpineSpy uses the camera briefly to check posture and processes frames on this Mac.'" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :NSCameraUseContinuityCameraDeviceType bool true" "$PLIST" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Set :NSCameraUseContinuityCameraDeviceType true" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString ${APP_VERSION}" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string ${APP_VERSION}" "$PLIST" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Set :CFBundleVersion ${APP_VERSION}" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string ${MINIMUM_SYSTEM_VERSION}" "$PLIST" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion ${MINIMUM_SYSTEM_VERSION}" "$PLIST"

if [[ "$CODESIGN_IDENTITY" == "-" ]]; then
    echo "Building an ad hoc development artifact; it is not eligible for public distribution."
    DEVELOPMENT_ENTITLEMENTS="build/development-entitlements.plist"
    cp entitlements.plist "$DEVELOPMENT_ENTITLEMENTS"
    /usr/libexec/PlistBuddy \
        -c "Add :com.apple.security.cs.disable-library-validation bool true" \
        "$DEVELOPMENT_ENTITLEMENTS"
    codesign --force --options runtime --entitlements "$DEVELOPMENT_ENTITLEMENTS" \
        --sign - dist/SpineSpy.app
    REQUIRE_DEVELOPER_ID=false
else
    security find-identity -v -p codesigning | grep -Fq "\"${CODESIGN_IDENTITY}\"" || {
        echo "Signing identity not found: ${CODESIGN_IDENTITY}" >&2
        exit 1
    }
    codesign --force --options runtime --timestamp --entitlements entitlements.plist \
        --sign "$CODESIGN_IDENTITY" dist/SpineSpy.app
    REQUIRE_DEVELOPER_ID=true
fi

EXPECTED_TEAM_ID="$EXPECTED_TEAM_ID" \
EXPECTED_IDENTITY="$CODESIGN_IDENTITY" \
EXPECTED_MINIMUM_SYSTEM_VERSION="$MINIMUM_SYSTEM_VERSION" \
REQUIRE_DEVELOPER_ID="$REQUIRE_DEVELOPER_ID" \
    ./scripts/verify_macos_app.sh dist/SpineSpy.app

SPINESPY_IMPORT_SMOKE_TEST=1 dist/SpineSpy.app/Contents/MacOS/SpineSpy

DMG_STAGE="dist/dmg"
mkdir -p "$DMG_STAGE"
cp -R dist/SpineSpy.app "$DMG_STAGE/"

create-dmg \
    --volname "SpineSpy" \
    --volicon "build/SpineSpy.icns" \
    --background "assets/dmg/background.tiff" \
    --window-pos 200 120 \
    --window-size 660 420 \
    --icon-size 112 \
    --icon "SpineSpy.app" 170 205 \
    --hide-extension "SpineSpy.app" \
    --app-drop-link 490 205 \
    "SpineSpy.dmg" \
    "$DMG_STAGE"

if [[ "$CODESIGN_IDENTITY" != "-" ]]; then
    codesign --force --timestamp --sign "$CODESIGN_IDENTITY" SpineSpy.dmg
else
    codesign --force --sign - SpineSpy.dmg
fi
codesign --verify --verbose=2 SpineSpy.dmg

DMG_SIZE_BYTES="$(stat -f%z SpineSpy.dmg)"
MAX_DMG_SIZE_BYTES="$((MAX_DMG_SIZE_MB * 1024 * 1024))"
if (( DMG_SIZE_BYTES > MAX_DMG_SIZE_BYTES )); then
    echo "SpineSpy.dmg is $((DMG_SIZE_BYTES / 1024 / 1024)) MB; limit is ${MAX_DMG_SIZE_MB} MB." >&2
    exit 1
fi

echo "Created SpineSpy.dmg ($((DMG_SIZE_BYTES / 1024 / 1024)) MB)."

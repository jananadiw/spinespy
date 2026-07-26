#!/bin/bash
set -euo pipefail

APP_PATH="${1:-}"
EXPECTED_TEAM_ID="${EXPECTED_TEAM_ID:-}"
EXPECTED_IDENTITY="${EXPECTED_IDENTITY:-}"
EXPECTED_MINIMUM_SYSTEM_VERSION="${EXPECTED_MINIMUM_SYSTEM_VERSION:-15.0}"
REQUIRE_DEVELOPER_ID="${REQUIRE_DEVELOPER_ID:-false}"

if [[ -z "$APP_PATH" || ! -d "$APP_PATH" ]]; then
    echo "Usage: $0 /path/to/App.app" >&2
    exit 1
fi

codesign --verify --deep --strict --verbose=2 "$APP_PATH"

PLIST="$APP_PATH/Contents/Info.plist"
[[ "$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' "$PLIST")" == "$EXPECTED_MINIMUM_SYSTEM_VERSION" ]] || {
    echo "LSMinimumSystemVersion must be ${EXPECTED_MINIMUM_SYSTEM_VERSION}." >&2
    exit 1
}

ENTITLEMENTS="$(codesign -d --entitlements :- "$APP_PATH" 2>/dev/null || true)"
grep -q 'com.apple.security.device.camera' <<<"$ENTITLEMENTS" || {
    echo "The app is missing the camera entitlement." >&2
    exit 1
}
if grep -q 'com.apple.security.get-task-allow' <<<"$ENTITLEMENTS"; then
    echo "Release app contains prohibited get-task-allow entitlement." >&2
    exit 1
fi
if [[ "$REQUIRE_DEVELOPER_ID" == "true" ]] && \
    grep -q 'com.apple.security.cs.disable-library-validation' <<<"$ENTITLEMENTS"; then
    echo "Release app contains prohibited disable-library-validation entitlement." >&2
    exit 1
fi
if [[ "$REQUIRE_DEVELOPER_ID" != "true" ]] && \
    ! grep -q 'com.apple.security.cs.disable-library-validation' <<<"$ENTITLEMENTS"; then
    echo "Ad hoc development app cannot load its separately signed Python framework." >&2
    exit 1
fi

MACHO_COUNT=0
while IFS= read -r -d '' FILE_PATH; do
    if ! file "$FILE_PATH" | grep -q 'Mach-O'; then
        continue
    fi
    MACHO_COUNT=$((MACHO_COUNT + 1))
    ARCHS="$(lipo -archs "$FILE_PATH")"
    if [[ "$ARCHS" != "arm64" ]]; then
        echo "Non-arm64 Mach-O: ${FILE_PATH} (${ARCHS})" >&2
        exit 1
    fi

    codesign --verify --strict "$FILE_PATH"
    DETAILS="$(codesign -dv --verbose=4 "$FILE_PATH" 2>&1)"
    FILE_ENTITLEMENTS="$(codesign -d --entitlements :- "$FILE_PATH" 2>/dev/null || true)"
    if grep -q 'com.apple.security.get-task-allow' <<<"$FILE_ENTITLEMENTS"; then
        echo "Prohibited get-task-allow entitlement: ${FILE_PATH}" >&2
        exit 1
    fi

    if [[ "$REQUIRE_DEVELOPER_ID" == "true" ]]; then
        grep -q 'flags=.*runtime' <<<"$DETAILS" || {
            echo "Hardened runtime missing: ${FILE_PATH}" >&2
            exit 1
        }
        grep -q '^Timestamp=' <<<"$DETAILS" || {
            echo "Secure timestamp missing: ${FILE_PATH}" >&2
            exit 1
        }
        grep -Fq "TeamIdentifier=${EXPECTED_TEAM_ID}" <<<"$DETAILS" || {
            echo "Unexpected Team ID: ${FILE_PATH}" >&2
            exit 1
        }
        grep -Fq "Authority=${EXPECTED_IDENTITY}" <<<"$DETAILS" || {
            echo "Unexpected signing identity: ${FILE_PATH}" >&2
            exit 1
        }
    fi
done < <(find "$APP_PATH" -type f -print0)

if (( MACHO_COUNT == 0 )); then
    echo "No Mach-O files found in ${APP_PATH}." >&2
    exit 1
fi

echo "Verified ${MACHO_COUNT} arm64 Mach-O files in ${APP_PATH}."

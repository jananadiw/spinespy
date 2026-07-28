#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMMAND="${1:-}"
RELEASE_TAG="${2:-}"
NOTARY_PROFILE="${NOTARY_PROFILE:-spinespy-notary}"
EXPECTED_TEAM_ID="${EXPECTED_TEAM_ID:-FWFFM858T2}"
CODESIGN_IDENTITY="${CODESIGN_IDENTITY:-Developer ID Application: Chathurika Wedagedara (${EXPECTED_TEAM_ID})}"

usage() {
    echo "Usage:" >&2
    echo "  $0 stage <existing-tag>" >&2
    echo "  CLEAN_MACOS15_VALIDATED=yes $0 publish <existing-tag>" >&2
    exit 1
}

[[ -n "$COMMAND" && -n "$RELEASE_TAG" ]] || usage
[[ "$COMMAND" == "stage" || "$COMMAND" == "publish" ]] || usage

cd "$ROOT_DIR"
command -v jq >/dev/null
gh auth status >/dev/null
REPOSITORY="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"

verify_downloaded_release() {
    local download_dir="$1"
    (
        cd "$download_dir"
        shasum -a 256 -c SpineSpy.dmg.sha256
        xcrun stapler validate SpineSpy.dmg
        codesign --verify --verbose=2 SpineSpy.dmg
        spctl --assess --type open \
            --context context:primary-signature \
            --verbose=2 SpineSpy.dmg
    )
}

if [[ "$COMMAND" == "publish" ]]; then
    [[ "${CLEAN_MACOS15_VALIDATED:-}" == "yes" ]] || {
        echo "Set CLEAN_MACOS15_VALIDATED=yes only after testing the downloaded draft asset on clean macOS 15." >&2
        exit 1
    }
    [[ "$(gh release view "$RELEASE_TAG" --repo "$REPOSITORY" --json isDraft --jq .isDraft)" == "true" ]] || {
        echo "Release ${RELEASE_TAG} is missing or is not a draft." >&2
        exit 1
    }
    VERIFY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/spinespy-publish.XXXXXX")"
    # shellcheck disable=SC2329  # Invoked indirectly by the EXIT trap below.
    cleanup_publish() {
        if [[ -n "${VERIFY_DIR:-}" && -d "$VERIFY_DIR" && "$VERIFY_DIR" == "${TMPDIR:-/tmp}/spinespy-publish."* ]]; then
            rm -rf -- "$VERIFY_DIR"
        fi
    }
    trap cleanup_publish EXIT
    gh release download "$RELEASE_TAG" --repo "$REPOSITORY" \
        --dir "$VERIFY_DIR" \
        --pattern "SpineSpy.dmg" \
        --pattern "SpineSpy.dmg.sha256"
    verify_downloaded_release "$VERIFY_DIR"
    gh release edit "$RELEASE_TAG" --repo "$REPOSITORY" --draft=false
    echo "Published https://github.com/${REPOSITORY}/releases/tag/${RELEASE_TAG}"
    exit 0
fi

if gh release view "$RELEASE_TAG" --repo "$REPOSITORY" >/dev/null 2>&1; then
    echo "GitHub release ${RELEASE_TAG} already exists; refusing to replace it." >&2
    exit 1
fi

git fetch --force origin "refs/tags/${RELEASE_TAG}:refs/tags/${RELEASE_TAG}"
TAG_COMMIT="$(git rev-parse --verify "${RELEASE_TAG}^{commit}")"
APP_VERSION="$(git show "${RELEASE_TAG}:pyproject.toml" | awk -F '"' '/^version = / { print $2; exit }')"
[[ "$RELEASE_TAG" == "v${APP_VERSION}" ]] || {
    echo "Tag ${RELEASE_TAG} does not match package version ${APP_VERSION}." >&2
    exit 1
}
NOTES_HEADING="$(git show "${RELEASE_TAG}:RELEASE_NOTES.md" | sed -n '1p')"
[[ "$NOTES_HEADING" == "# SpineSpy ${APP_VERSION}" ]] || {
    echo "Release notes must start with '# SpineSpy ${APP_VERSION}'." >&2
    exit 1
}

security find-identity -v -p codesigning | grep -Fq "\"${CODESIGN_IDENTITY}\"" || {
    echo "Required signing identity not found: ${CODESIGN_IDENTITY}" >&2
    exit 1
}
[[ "$CODESIGN_IDENTITY" == *"(${EXPECTED_TEAM_ID})" ]] || {
    echo "Signing identity does not use Team ID ${EXPECTED_TEAM_ID}." >&2
    exit 1
}
xcrun notarytool history --keychain-profile "$NOTARY_PROFILE" >/dev/null

RELEASE_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/spinespy-release.XXXXXX")"
RELEASE_DIR="${RELEASE_PARENT}/worktree"
cleanup() {
    git -C "$ROOT_DIR" worktree remove --force "$RELEASE_DIR" >/dev/null 2>&1 || true
    if [[ -n "${RELEASE_PARENT:-}" && -d "$RELEASE_PARENT" && "$RELEASE_PARENT" == "${TMPDIR:-/tmp}/spinespy-release."* ]]; then
        rm -rf -- "$RELEASE_PARENT"
    fi
}
trap cleanup EXIT

git worktree add --detach "$RELEASE_DIR" "$TAG_COMMIT"
cd "$RELEASE_DIR"
mkdir -p release-artifacts

poetry env use python3.11
poetry install --with dev --no-interaction
./scripts/download_models.sh
poetry run pytest -q
CODESIGN_IDENTITY="$CODESIGN_IDENTITY" \
EXPECTED_TEAM_ID="$EXPECTED_TEAM_ID" \
MAX_DMG_SIZE_MB=200 \
    ./build_dmg.sh

xcrun notarytool submit SpineSpy.dmg \
    --keychain-profile "$NOTARY_PROFILE" \
    --wait \
    --output-format json \
    > release-artifacts/notary-submission.json
SUBMISSION_ID="$(jq -er '.id' release-artifacts/notary-submission.json)"
[[ "$(jq -er '.status' release-artifacts/notary-submission.json)" == "Accepted" ]] || {
    echo "Apple did not accept the notarization submission ${SUBMISSION_ID}." >&2
    exit 1
}
xcrun notarytool log "$SUBMISSION_ID" \
    --keychain-profile "$NOTARY_PROFILE" \
    release-artifacts/notarization-log.json
poetry run python scripts/validate_notarization_log.py \
    release-artifacts/notarization-log.json

xcrun stapler staple SpineSpy.dmg
xcrun stapler validate SpineSpy.dmg
codesign --verify --verbose=2 SpineSpy.dmg
spctl --assess --type open \
    --context context:primary-signature \
    --verbose=2 SpineSpy.dmg

FINAL_SHA256="$(shasum -a 256 SpineSpy.dmg | awk '{print $1}')"
echo "${FINAL_SHA256}  SpineSpy.dmg" > release-artifacts/SpineSpy.dmg.sha256

MACOS_VERSION="$(sw_vers -productVersion)"
XCODE_VERSION="$(xcodebuild -version | paste -sd ';' -)"
PYTHON_VERSION="$(poetry run python --version)"
POETRY_VERSION="$(poetry --version)"
CREATE_DMG_VERSION="$(create-dmg --version 2>&1 | head -1)"
jq -n \
    --arg tag "$RELEASE_TAG" \
    --arg commit "$TAG_COMMIT" \
    --arg version "$APP_VERSION" \
    --arg sha256 "$FINAL_SHA256" \
    --arg notarySubmissionId "$SUBMISSION_ID" \
    --arg macOS "$MACOS_VERSION" \
    --arg xcode "$XCODE_VERSION" \
    --arg python "$PYTHON_VERSION" \
    --arg poetry "$POETRY_VERSION" \
    --arg createDmg "$CREATE_DMG_VERSION" \
    '{
        tag: $tag,
        commit: $commit,
        version: $version,
        artifact: "SpineSpy.dmg",
        sha256: $sha256,
        notarySubmissionId: $notarySubmissionId,
        toolchain: {
            macOS: $macOS,
            xcode: $xcode,
            python: $python,
            poetry: $poetry,
            createDmg: $createDmg
        }
    }' > release-artifacts/release-manifest.json

gh release create "$RELEASE_TAG" \
    "SpineSpy.dmg#SpineSpy.dmg" \
    "release-artifacts/SpineSpy.dmg.sha256#SpineSpy.dmg.sha256" \
    "release-artifacts/release-manifest.json#release-manifest.json" \
    "release-artifacts/notary-submission.json#notary-submission.json" \
    "release-artifacts/notarization-log.json#notarization-log.json" \
    --repo "$REPOSITORY" \
    --verify-tag \
    --draft \
    --title "SpineSpy ${RELEASE_TAG}" \
    --notes-file "$RELEASE_DIR/RELEASE_NOTES.md"

VERIFY_DIR="${RELEASE_PARENT}/downloaded"
mkdir -p "$VERIFY_DIR"
gh release download "$RELEASE_TAG" --repo "$REPOSITORY" \
    --dir "$VERIFY_DIR" \
    --pattern "SpineSpy.dmg" \
    --pattern "SpineSpy.dmg.sha256"
verify_downloaded_release "$VERIFY_DIR"

echo "Draft staged at https://github.com/${REPOSITORY}/releases/tag/${RELEASE_TAG}"
echo "Test the downloaded DMG on clean macOS 15, then run:"
echo "CLEAN_MACOS15_VALIDATED=yes ./scripts/release_local.sh publish ${RELEASE_TAG}"

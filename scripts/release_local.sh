#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE_TAG="${1:-}"
NOTARY_PROFILE="${NOTARY_PROFILE:-spinespy-notary}"

if [[ -z "$RELEASE_TAG" ]]; then
    echo "Usage: $0 <existing-tag>" >&2
    exit 1
fi

cd "$ROOT_DIR"

gh auth status >/dev/null
REPOSITORY="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
git fetch origin "refs/tags/${RELEASE_TAG}:refs/tags/${RELEASE_TAG}"
git rev-parse --verify "${RELEASE_TAG}^{commit}" >/dev/null

APP_VERSION="$(git show "${RELEASE_TAG}:pyproject.toml" | awk -F '"' '/^version = / { print $2; exit }')"
if [[ "$RELEASE_TAG" != "v${APP_VERSION}" ]]; then
    echo "Tag ${RELEASE_TAG} does not match package version ${APP_VERSION}." >&2
    exit 1
fi

if gh release view "$RELEASE_TAG" --repo "$REPOSITORY" >/dev/null 2>&1; then
    echo "GitHub release ${RELEASE_TAG} already exists." >&2
    exit 1
fi

CODESIGN_IDENTITY="${CODESIGN_IDENTITY:-$(security find-identity -v -p codesigning | sed -n 's/.*"\(Developer ID Application:.*\)"/\1/p' | head -1)}"
if [[ -z "$CODESIGN_IDENTITY" ]]; then
    echo "No Developer ID Application signing identity was found." >&2
    exit 1
fi

if ! xcrun notarytool history --keychain-profile "$NOTARY_PROFILE" >/dev/null 2>&1; then
    echo "Notary profile '${NOTARY_PROFILE}' is missing or invalid." >&2
    echo "Create it with: xcrun notarytool store-credentials '${NOTARY_PROFILE}'" >&2
    exit 1
fi

RELEASE_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/spinespy-release.XXXXXX")"
RELEASE_DIR="${RELEASE_PARENT}/worktree"
cleanup() {
    git -C "$ROOT_DIR" worktree remove --force "$RELEASE_DIR" >/dev/null 2>&1 || true
    rmdir "$RELEASE_PARENT" >/dev/null 2>&1 || true
}
trap cleanup EXIT

git worktree add --detach "$RELEASE_DIR" "$RELEASE_TAG"
cd "$RELEASE_DIR"

poetry install --with dev --no-interaction
./scripts/download_models.sh
poetry run pytest -q
CODESIGN_IDENTITY="$CODESIGN_IDENTITY" MAX_DMG_SIZE_MB=200 ./build_dmg.sh

xcrun notarytool submit SpineSpy.dmg \
    --keychain-profile "$NOTARY_PROFILE" \
    --wait
xcrun stapler staple SpineSpy.dmg
xcrun stapler validate SpineSpy.dmg
codesign --verify --verbose=2 SpineSpy.dmg
spctl --assess --type open \
    --context context:primary-signature \
    --verbose=2 SpineSpy.dmg

gh release create "$RELEASE_TAG" "SpineSpy.dmg#SpineSpy.dmg" \
    --repo "$REPOSITORY" \
    --verify-tag \
    --title "SpineSpy ${RELEASE_TAG}" \
    --notes-file "$ROOT_DIR/RELEASE_NOTES.md"

echo "Published https://github.com/${REPOSITORY}/releases/tag/${RELEASE_TAG}"

#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

download_model() {
    local destination="$1"
    local url="$2"
    local expected_sha256="$3"
    local temporary_file

    if [[ -f "$destination" ]] && [[ "$(shasum -a 256 "$destination" | awk '{print $1}')" == "$expected_sha256" ]]; then
        echo "✓ $destination already verified"
        return
    fi

    temporary_file="$(mktemp "${TMPDIR:-/tmp}/spinespy-model.XXXXXX")"
    trap 'rm -f "$temporary_file"' RETURN
    curl --fail --location --silent --show-error --output "$temporary_file" "$url"

    local actual_sha256
    actual_sha256="$(shasum -a 256 "$temporary_file" | awk '{print $1}')"
    if [[ "$actual_sha256" != "$expected_sha256" ]]; then
        echo "Checksum mismatch for $destination" >&2
        echo "Expected: $expected_sha256" >&2
        echo "Actual:   $actual_sha256" >&2
        exit 1
    fi

    mv "$temporary_file" "$destination"
    trap - RETURN
    echo "✓ Downloaded and verified $destination"
}

download_model \
    "pose_landmarker.task" \
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task" \
    "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"

download_model \
    "efficientdet_lite0.tflite" \
    "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite" \
    "0720bf247bd76e6594ea28fa9c6f7c5242be774818997dbbeffc4da460c723bb"

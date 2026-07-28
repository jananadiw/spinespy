#!/usr/bin/env python3
"""Fail a release for a rejected notarization or an unknown issue."""

import json
import pathlib
import re
import sys


ALLOWED_WARNING_PATH = (
    "SpineSpy.dmg/SpineSpy.app/Contents/Resources/"
    "pose_landmarker.task/pose_detector.tflite"
)
ALLOWED_WARNING_MESSAGE = re.compile(
    r"^The archive at .+/pose_landmarker\.task/pose_detector\.tflite "
    r"could not be unpacked\. Any executables contained in the archive "
    r"will not be notarized\.$"
)


def validate(log):
    if log.get("status") != "Accepted":
        raise ValueError(f"Notarization status is {log.get('status')!r}, not 'Accepted'.")

    for issue in log.get("issues", []):
        allowed = (
            issue.get("severity") == "warning"
            and issue.get("code") is None
            and issue.get("path") == ALLOWED_WARNING_PATH
            and issue.get("architecture") is None
            and ALLOWED_WARNING_MESSAGE.fullmatch(issue.get("message", ""))
        )
        if not allowed:
            raise ValueError(
                "Unexpected notarization issue: "
                f"{json.dumps(issue, sort_keys=True)}"
            )


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} notarization-log.json")
    path = pathlib.Path(sys.argv[1])
    try:
        log = json.loads(path.read_text())
        validate(log)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Validated notarization log: {path}")


if __name__ == "__main__":
    main()

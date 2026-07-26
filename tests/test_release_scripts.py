"""Release-pipeline policy and failure-path tests."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.validate_notarization_log import validate


ROOT = Path(__file__).resolve().parents[1]


def _write_executable(path, body):
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)


def _run(script, *arguments, env=None):
    return subprocess.run(
        [str(ROOT / script), *arguments],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_shell_scripts_parse():
    for script in (
        "build_dmg.sh",
        "scripts/release_local.sh",
        "scripts/verify_macos_app.sh",
    ):
        subprocess.run(["bash", "-n", ROOT / script], check=True)


def test_build_rejects_non_arm64_before_mutating_outputs(tmp_path):
    _write_executable(tmp_path / "uname", 'echo "x86_64"')
    result = _run(
        "build_dmg.sh",
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
    )

    assert result.returncode != 0
    assert "native Apple Silicon" in result.stderr


def test_publish_requires_explicit_clean_macos_validation(tmp_path):
    _write_executable(
        tmp_path / "gh",
        """
if [ "$1" = "auth" ]; then exit 0; fi
if [ "$1" = "repo" ]; then echo "jananadiw/spinespy"; exit 0; fi
exit 1
""",
    )
    result = _run(
        "scripts/release_local.sh",
        "publish",
        "v1.2.3",
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "CLEAN_MACOS15_VALIDATED": "",
        },
    )

    assert result.returncode != 0
    assert "CLEAN_MACOS15_VALIDATED=yes" in result.stderr


def test_release_uses_tag_worktree_notes_and_draft_staging():
    script = (ROOT / "scripts/release_local.sh").read_text()

    assert '--notes-file "$RELEASE_DIR/RELEASE_NOTES.md"' in script
    assert "--draft" in script
    assert script.index("xcrun stapler staple") < script.index("FINAL_SHA256=")
    assert script.index("FINAL_SHA256=") < script.index("gh release create")
    assert script.index("gh release download") < script.index(
        'verify_downloaded_release "$VERIFY_DIR"'
    )


def test_ad_hoc_build_smoke_tests_python_framework_without_weakening_release():
    build_script = (ROOT / "build_dmg.sh").read_text()
    verifier = (ROOT / "scripts/verify_macos_app.sh").read_text()

    assert "com.apple.security.cs.disable-library-validation" in build_script
    assert "SPINESPY_IMPORT_SMOKE_TEST=1" in build_script
    assert "REQUIRE_DEVELOPER_ID" in verifier
    assert "prohibited disable-library-validation entitlement" in verifier


def test_known_model_unpack_warning_is_allowed():
    validate(
        {
            "status": "Accepted",
            "issues": [
                {
                    "severity": "warning",
                    "code": None,
                    "path": (
                        "SpineSpy.dmg/SpineSpy.app/Contents/Resources/"
                        "pose_landmarker.task/pose_detector.tflite"
                    ),
                    "message": (
                        "The archive at SpineSpy.dmg/SpineSpy.app/Contents/"
                        "Resources/pose_landmarker.task/pose_detector.tflite "
                        "could not be unpacked. Any executables contained in "
                        "the archive will not be notarized."
                    ),
                    "architecture": None,
                }
            ],
        }
    )


@pytest.mark.parametrize(
    "log",
    [
        {"status": "Invalid", "issues": []},
        {
            "status": "Accepted",
            "issues": [
                {
                    "severity": "warning",
                    "code": None,
                    "path": "SpineSpy.dmg/unexpected.zip",
                    "message": "The archive could not be unpacked.",
                    "architecture": None,
                }
            ],
        },
        {
            "status": "Accepted",
            "issues": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "path": "SpineSpy.app",
                    "message": "The signature is invalid.",
                    "architecture": "arm64",
                }
            ],
        },
    ],
)
def test_unknown_or_rejected_notarization_fails(log):
    with pytest.raises(ValueError):
        validate(log)


def test_notarization_cli_rejects_malformed_json(tmp_path):
    log_path = tmp_path / "log.json"
    log_path.write_text("{")

    result = subprocess.run(
        [
            os.environ.get("PYTHON", "python3"),
            ROOT / "scripts/validate_notarization_log.py",
            log_path,
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0


def test_release_manifest_shape_is_json_serializable():
    manifest = {
        "tag": "v1.2.3",
        "commit": "abc123",
        "version": "1.2.3",
        "artifact": "SpineSpy.dmg",
        "sha256": "0" * 64,
        "notarySubmissionId": "submission-id",
        "toolchain": {
            "macOS": "15.0",
            "xcode": "Xcode 16",
            "python": "Python 3.11",
            "poetry": "Poetry 2.3.1",
            "createDmg": "create-dmg 1.3.0",
        },
    }

    assert json.loads(json.dumps(manifest))["artifact"] == "SpineSpy.dmg"

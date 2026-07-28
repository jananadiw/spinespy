"""Tests for stable macOS camera discovery and selection."""

from unittest.mock import patch

import pytest

from spinespy.camera import (
    BUILT_IN_CAMERA_TYPE,
    CameraDevice,
    CameraSelectionError,
    discover_cameras,
    select_camera,
)


def _camera(unique_id, name, device_type, index):
    return CameraDevice(unique_id, name, device_type, index)


def test_default_selects_builtin_instead_of_first_continuity_camera():
    devices = (
        _camera("a-phone", "iPhone Camera", "AVCaptureDeviceTypeExternal", 0),
        _camera("z-mac", "FaceTime HD Camera", BUILT_IN_CAMERA_TYPE, 1),
    )

    assert select_camera(devices, None) == devices[1]


def test_explicit_external_camera_selection_is_allowed():
    devices = (
        _camera("a-phone", "iPhone Camera", "AVCaptureDeviceTypeExternal", 0),
        _camera("z-mac", "FaceTime HD Camera", BUILT_IN_CAMERA_TYPE, 1),
    )

    assert select_camera(devices, "a-phone") == devices[0]


def test_missing_saved_camera_does_not_silently_fallback():
    devices = (
        _camera("mac", "FaceTime HD Camera", BUILT_IN_CAMERA_TYPE, 0),
    )

    with pytest.raises(CameraSelectionError, match="not connected"):
        select_camera(devices, "missing")


def test_external_only_setup_requires_explicit_selection():
    devices = (
        _camera("external", "USB Camera", "AVCaptureDeviceTypeExternal", 0),
    )

    with pytest.raises(CameraSelectionError, match="No built-in Mac camera"):
        select_camera(devices, None)


def test_discovery_matches_opencv_unique_id_order_and_skips_disconnected():
    class Device:
        def __init__(self, unique_id, name, device_type, connected=True):
            self._unique_id = unique_id
            self._name = name
            self._device_type = device_type
            self._connected = connected

        def uniqueID(self):
            return self._unique_id

        def localizedName(self):
            return self._name

        def deviceType(self):
            return self._device_type

        def isConnected(self):
            return self._connected

    devices = [
        Device("z-mac", "FaceTime HD Camera", BUILT_IN_CAMERA_TYPE),
        Device("unused", "Disconnected Camera", "external", connected=False),
        Device("a-phone", "iPhone Camera", "external"),
    ]

    class CaptureDevice:
        @classmethod
        def devicesWithMediaType_(cls, media_type):
            if media_type == "video":
                return devices
            assert media_type == "muxed"
            return []

    class FakeAVFoundation:
        AVMediaTypeVideo = "video"
        AVMediaTypeMuxed = "muxed"
        AVCaptureDevice = CaptureDevice

    with (
        patch("spinespy.camera.sys.platform", "darwin"),
        patch("spinespy.camera.AVFoundation", FakeAVFoundation),
    ):
        discovered = discover_cameras()

    assert [(device.unique_id, device.opencv_index) for device in discovered] == [
        ("a-phone", 0),
        ("z-mac", 1),
    ]

"""macOS camera discovery, identity, and authorization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import sys

try:
    import AVFoundation
except ImportError:  # pragma: no cover - source execution on non-macOS hosts
    AVFoundation = None

BUILT_IN_CAMERA_TYPE = "AVCaptureDeviceTypeBuiltInWideAngleCamera"


class CameraAuthorization(Enum):
    AUTHORIZED = "authorized"
    NOT_DETERMINED = "not_determined"
    DENIED = "denied"
    RESTRICTED = "restricted"
    UNAVAILABLE = "unavailable"


class CameraSelectionError(RuntimeError):
    """Raised when SpineSpy cannot resolve a safe camera selection."""


@dataclass(frozen=True)
class CameraDevice:
    unique_id: str
    name: str
    device_type: str
    opencv_index: int

    @property
    def is_builtin(self) -> bool:
        return self.device_type == BUILT_IN_CAMERA_TYPE


def discover_cameras() -> tuple[CameraDevice, ...]:
    """Return connected video devices in OpenCV AVFoundation index order."""
    if sys.platform != "darwin" or AVFoundation is None:
        return ()

    # OpenCV's macOS backend builds this exact Video + Muxed list, then sorts
    # it by unique ID. A broader DiscoverySession also returns Desk View, which
    # OpenCV cannot address and would shift every later numeric index.
    devices = (
        list(
            AVFoundation.AVCaptureDevice.devicesWithMediaType_(
                AVFoundation.AVMediaTypeVideo
            )
        )
        + list(
            AVFoundation.AVCaptureDevice.devicesWithMediaType_(
                AVFoundation.AVMediaTypeMuxed
            )
        )
    )
    devices = sorted(
        (device for device in devices if device.isConnected()),
        key=lambda device: str(device.uniqueID()),
    )
    return tuple(
        CameraDevice(
            unique_id=str(device.uniqueID()),
            name=str(device.localizedName()),
            device_type=str(device.deviceType()),
            opencv_index=index,
        )
        for index, device in enumerate(devices)
    )


def select_camera(
    devices: tuple[CameraDevice, ...],
    selected_unique_id: str | None,
) -> CameraDevice:
    """Resolve an explicit camera or safely default to built-in Mac hardware."""
    if selected_unique_id is not None:
        for device in devices:
            if device.unique_id == selected_unique_id:
                return device
        raise CameraSelectionError(
            "The selected camera is not connected. Choose another camera in Settings."
        )

    for device in devices:
        if device.is_builtin:
            return device

    raise CameraSelectionError(
        "No built-in Mac camera is available. Choose a camera in Settings before monitoring."
    )


def camera_authorization_status() -> CameraAuthorization:
    """Read the current macOS camera authorization without prompting."""
    if sys.platform != "darwin" or AVFoundation is None:
        return CameraAuthorization.UNAVAILABLE

    status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
        AVFoundation.AVMediaTypeVideo
    )
    return {
        AVFoundation.AVAuthorizationStatusAuthorized: CameraAuthorization.AUTHORIZED,
        AVFoundation.AVAuthorizationStatusNotDetermined: (
            CameraAuthorization.NOT_DETERMINED
        ),
        AVFoundation.AVAuthorizationStatusDenied: CameraAuthorization.DENIED,
        AVFoundation.AVAuthorizationStatusRestricted: CameraAuthorization.RESTRICTED,
    }.get(status, CameraAuthorization.UNAVAILABLE)


def request_camera_access(callback) -> None:
    """Request camera access and invoke callback with the resulting grant."""
    status = camera_authorization_status()
    if status is CameraAuthorization.AUTHORIZED:
        callback(True)
        return
    if status is not CameraAuthorization.NOT_DETERMINED:
        callback(False)
        return

    AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
        AVFoundation.AVMediaTypeVideo,
        lambda granted: callback(bool(granted)),
    )

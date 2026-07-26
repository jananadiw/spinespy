import rumps
import cv2
import mediapipe as mp
import objc
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os
import sys
import time
import threading
import statistics
import random
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum

from PyObjCTools import AppHelper

from spinespy.settings import AppSettings, CalibrationSettings, SettingsStore

try:
    from AppKit import (
        NSAccessibilityPostNotification,
        NSAccessibilityPostNotificationWithUserInfo,
        NSAccessibilityAnnouncementKey,
        NSAccessibilityAnnouncementRequestedNotification,
        NSAccessibilityPriorityKey,
        NSAccessibilityPriorityMedium,
        NSAccessibilityValueChangedNotification,
        NSApplication,
        NSBackingStoreBuffered,
        NSColor,
        NSFloatingWindowLevel,
        NSFont,
        NSImage,
        NSImageScaleProportionallyUpOrDown,
        NSImageView,
        NSMakeRect,
        NSModalResponseOK,
        NSPanel,
        NSSavePanel,
        NSScreen,
        NSTextField,
        NSView,
        NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSWindowCollectionBehaviorFullScreenAuxiliary,
        NSWindowCollectionBehaviorStationary,
        NSWindowStyleMaskBorderless,
        NSWindowStyleMaskNonactivatingPanel,
    )
    from UniformTypeIdentifiers import UTTypeJPEG, UTTypePNG
except ImportError:
    NSPanel = None


if NSPanel is not None:

    class DraggablePetImageView(NSImageView):
        def acceptsFirstMouse_(self, event):
            return True

        def mouseDown_(self, event):
            window = self.window()
            if window is not None:
                window.performWindowDragWithEvent_(event)


    class DraggablePetMessageField(NSTextField):
        def acceptsFirstMouse_(self, event):
            return True

        def mouseDown_(self, event):
            window = self.window()
            if window is not None:
                window.performWindowDragWithEvent_(event)


    class DraggablePetBubbleView(NSView):
        def acceptsFirstMouse_(self, event):
            return True

        def mouseDown_(self, event):
            window = self.window()
            if window is not None:
                window.performWindowDragWithEvent_(event)

        def refreshAppearance(self):
            if self.layer() is not None:
                self.layer().setBackgroundColor_(NSColor.controlBackgroundColor().CGColor())

        def viewDidChangeEffectiveAppearance(self):
            objc.super(DraggablePetBubbleView, self).viewDidChangeEffectiveAppearance()
            self.refreshAppearance()


else:
    DraggablePetImageView = None
    DraggablePetMessageField = None
    DraggablePetBubbleView = None


def resource_path(relative_path):
    """Get path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


# Icons
ICON_GOOD = "🦸"
ICON_BAD = "🧟"
PET_IMAGE_FILES = {
    "good": "assets/pets/posture-good.png",
    "bad": "assets/pets/posture-bad.png",
}
PET_MESSAGES = {
    "good": "Sitting nice and straight!",
    "bad": "You're being a shrimp, my friend.",
    "checking": "Camera on briefly. Checking posture...",
    "calibrating": "Hold still. Finding your baseline...",
    "paused": "Taking a posture break.",
}
PET_BUBBLE_SIZE = (224, 42)

# Detection config
SLOUCH_THRESHOLD = 0.1
TILT_THRESHOLD = 0.05
BAD_STREAK_LIMIT = 5

# Alert audio clips
ALERT_SOUND_FILES = [
    "assets/audio/Come on, shoulders back.mp3",
    "assets/audio/auditioning to be a shrimp.mp3",
    "assets/audio/did gravity offend u.mp3",
    "assets/audio/slouching_bella.mp3",
    "assets/audio/writing in cursive.mp3",
    "assets/audio/you're not a croissant.mp3",
]

# Calibration config
CALIBRATION_FRAMES = 10
CALIBRATION_INTERVAL = 0.3

# Calibration baseline (set via calibrate())
baseline_lean = 0.0
baseline_tilt = 0.0
effective_slouch_threshold = SLOUCH_THRESHOLD
effective_tilt_threshold = TILT_THRESHOLD

POSE_MODEL_PATH = resource_path("pose_landmarker.task")
PHONE_MODEL_PATH = resource_path("efficientdet_lite0.tflite")
PHONE_SCORE_THRESHOLD = 0.35

pose_detector = None
phone_detector = None
_detector_lock = threading.Lock()


class Operation(Enum):
    MONITORING = "monitoring"
    CALIBRATING = "calibrating"
    SAVING = "saving"


@dataclass(frozen=True)
class OperationResult:
    succeeded: bool
    value: object = None
    message: str = ""


class OperationCoordinator:
    """Reserve one operation and reject stale results after pause or shutdown."""

    def __init__(self):
        self._lock = threading.Lock()
        self._next_token = 0
        self._active_token = None
        self._accepted_token = None
        self._shutting_down = False

    def reserve(self):
        with self._lock:
            if self._shutting_down or self._active_token is not None:
                return None
            self._next_token += 1
            self._active_token = self._next_token
            self._accepted_token = self._next_token
            return self._next_token

    def accepts(self, token):
        with self._lock:
            return not self._shutting_down and self._accepted_token == token

    def invalidate_result(self):
        with self._lock:
            self._accepted_token = None

    def finish(self, token):
        with self._lock:
            accepted = not self._shutting_down and self._accepted_token == token
            if self._active_token == token:
                self._active_token = None
            if self._accepted_token == token:
                self._accepted_token = None
            return accepted

    def begin_shutdown(self):
        with self._lock:
            self._shutting_down = True
            self._accepted_token = None


def _require_model(path, label):
    if os.path.exists(path):
        return
    raise RuntimeError(
        f"Missing {label} model at {path}. Run ./scripts/download_models.sh, then restart SpineSpy."
    )


def _get_pose_detector():
    global pose_detector
    if pose_detector is not None:
        return pose_detector
    with _detector_lock:
        if pose_detector is None:
            _require_model(POSE_MODEL_PATH, "pose")
            options = vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=POSE_MODEL_PATH),
                output_segmentation_masks=False,
            )
            pose_detector = vision.PoseLandmarker.create_from_options(options)
    return pose_detector


def _get_phone_detector():
    global phone_detector
    if phone_detector is not None:
        return phone_detector
    with _detector_lock:
        if phone_detector is None:
            _require_model(PHONE_MODEL_PATH, "phone detection")
            options = vision.ObjectDetectorOptions(
                base_options=python.BaseOptions(model_asset_path=PHONE_MODEL_PATH),
                category_allowlist=["cell phone"],
                max_results=3,
                score_threshold=PHONE_SCORE_THRESHOLD,
            )
            phone_detector = vision.ObjectDetector.create_from_options(options)
    return phone_detector


def close_detectors():
    """Close initialized MediaPipe tasks during orderly shutdown."""
    global pose_detector, phone_detector
    with _detector_lock:
        for detector in (pose_detector, phone_detector):
            close = getattr(detector, "close", None)
            if close is not None:
                close()
        pose_detector = None
        phone_detector = None


def camera_permission_hint():
    """Return an actionable camera-access hint for the current platform."""
    if sys.platform == "darwin":
        return (
            "macOS likely blocked camera access. Enable it in System Settings > Privacy & Security > "
            "Camera for the exact app/process running SpineSpy (Terminal, iTerm, Python, or SpineSpy.app)."
        )
    return "Camera is unavailable, already in use by another app, or not permitted."


def open_camera():
    """Open the system default camera."""
    if sys.platform == "darwin":
        return cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
    return cv2.VideoCapture(0)


def _notify_camera_state(callback, state):
    if callback is not None:
        callback(state)


def get_posture_metrics(landmarks):
    """Extract forward lean and tilt from landmarks."""
    nose = landmarks[0]
    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]

    shoulder_z = (left_shoulder.z + right_shoulder.z) / 2
    forward_lean = shoulder_z - nose.z
    tilt = abs(left_shoulder.y - right_shoulder.y)
    return forward_lean, tilt


def calibrate(camera_state_callback=None, cancel_event=None):
    """Capture multiple frames and compute a robust baseline from median metrics."""
    global baseline_lean, baseline_tilt, effective_slouch_threshold, effective_tilt_threshold
    _notify_camera_state(camera_state_callback, "opening")
    cap = open_camera()
    if not cap.isOpened():
        cap.release()
        _notify_camera_state(camera_state_callback, "off")
        print(f"Calibration failed: camera error. {camera_permission_hint()}")
        return False

    _notify_camera_state(camera_state_callback, "on")
    try:
        time.sleep(0.5)
        for _ in range(5):
            cap.read()

        detector = _get_pose_detector()
        leans = []
        tilts = []
        for _ in range(CALIBRATION_FRAMES):
            if cancel_event is not None and cancel_event.is_set():
                return False
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            results = detector.detect(mp_image)
            if results.pose_landmarks and len(results.pose_landmarks) > 0:
                lean, tilt = get_posture_metrics(results.pose_landmarks[0])
                leans.append(lean)
                tilts.append(tilt)
            time.sleep(CALIBRATION_INTERVAL)
    finally:
        cap.release()
        _notify_camera_state(camera_state_callback, "off")

    if len(leans) < CALIBRATION_FRAMES // 2:
        print(f"Calibration failed: only {len(leans)} valid frames (need {CALIBRATION_FRAMES // 2})")
        return False

    baseline_lean = statistics.median(leans)
    baseline_tilt = statistics.median(tilts)

    lean_std = statistics.stdev(leans) if len(leans) > 1 else 0.0
    tilt_std = statistics.stdev(tilts) if len(tilts) > 1 else 0.0
    effective_slouch_threshold = max(SLOUCH_THRESHOLD, lean_std * 3)
    effective_tilt_threshold = max(TILT_THRESHOLD, tilt_std * 3)

    print(f"✓ Calibrated from {len(leans)} frames: baseline_lean={baseline_lean:.3f}, baseline_tilt={baseline_tilt:.3f}")
    print(f"  Adaptive thresholds: slouch={effective_slouch_threshold:.3f}, tilt={effective_tilt_threshold:.3f}")
    return True


def _severity_label(delta, threshold):
    ratio = delta / threshold if threshold > 0 else 0
    if ratio < 1.5:
        return "mild"
    if ratio < 2.5:
        return "moderate"
    return "severe"


def check_posture(landmarks):
    """Check for slouching and side tilt relative to calibrated baseline."""
    forward_lean, tilt = get_posture_metrics(landmarks)
    lean_delta = forward_lean - baseline_lean
    tilt_delta = tilt - baseline_tilt

    print(f"  [DEBUG] lean_delta={lean_delta:.3f} (threshold={effective_slouch_threshold:.3f}), tilt_delta={tilt_delta:.3f} (threshold={effective_tilt_threshold:.3f})")

    if lean_delta >= effective_slouch_threshold:
        severity = _severity_label(lean_delta, effective_slouch_threshold)
        return True, f"Slouching ({severity})"
    if tilt_delta >= effective_tilt_threshold:
        severity = _severity_label(tilt_delta, effective_tilt_threshold)
        return True, f"Tilting ({severity})"
    return False, None


def get_phone_detections(frame):
    """Return MediaPipe cell-phone detections for a BGR camera frame."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    return _get_phone_detector().detect(mp_image).detections


def detect_phone(frame):
    """Detect a cell phone in a BGR camera frame using MediaPipe."""
    for detection in get_phone_detections(frame):
        if not detection.categories:
            continue
        category = detection.categories[0]
        print(f"  [DEBUG] Detected {category.category_name}, confidence={category.score:.2f}")
        if category.category_name == "cell phone":
            print(f"  [DEBUG] ✓ Phone detected! confidence={category.score:.2f}")
            return True
    print("  [DEBUG] No phone detected")
    return False


SNAPSHOT_FRAMES = 3


def take_snapshot(camera_state_callback=None, cancel_event=None):
    """Capture multiple frames, analyze with majority voting, return result."""
    _notify_camera_state(camera_state_callback, "opening")
    cap = open_camera()
    if not cap.isOpened():
        cap.release()
        _notify_camera_state(camera_state_callback, "off")
        print(f"Snapshot failed: camera error. {camera_permission_hint()}")
        return None, "Camera error"

    _notify_camera_state(camera_state_callback, "on")
    try:
        time.sleep(0.5)
        for _ in range(5):
            cap.read()

        frames = []
        for _ in range(SNAPSHOT_FRAMES):
            if cancel_event is not None and cancel_event.is_set():
                return None, "Cancelled"
            ret, frame = cap.read()
            if ret:
                frames.append(cv2.flip(frame, 1))
    finally:
        cap.release()
        _notify_camera_state(camera_state_callback, "off")

    if not frames:
        return None, "Capture failed"

    detector = _get_pose_detector()
    bad_votes = []
    reasons = []
    for frame in frames:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        pose_results = detector.detect(mp_image)

        if pose_results.pose_landmarks and len(pose_results.pose_landmarks) > 0:
            posture_bad, reason = check_posture(pose_results.pose_landmarks[0])
            bad_votes.append(posture_bad)
            if posture_bad:
                reasons.append(reason)
        else:
            bad_votes.append(False)

    bad_count = sum(bad_votes)
    print(f"[DEBUG] Posture votes: {bad_count}/{len(bad_votes)} bad")

    if bad_count >= len(bad_votes) / 2 and reasons:
        dominant_reason = Counter(reasons).most_common(1)[0][0]
        return True, dominant_reason

    phone_found = detect_phone(frames[-1])
    print(f"[DEBUG] Phone detected: {phone_found}")

    if phone_found:
        return True, "Phone detected"

    return False, "Good posture"


def save_camera_frame(path, camera_state_callback=None, cancel_event=None):
    """Capture one frame and save it without running posture or phone inference."""
    _notify_camera_state(camera_state_callback, "opening")
    cap = open_camera()
    if not cap.isOpened():
        cap.release()
        _notify_camera_state(camera_state_callback, "off")
        return OperationResult(False, message=f"Camera error. {camera_permission_hint()}")

    _notify_camera_state(camera_state_callback, "on")
    try:
        time.sleep(0.5)
        for _ in range(5):
            if cancel_event is not None and cancel_event.is_set():
                return OperationResult(False, message="Snapshot cancelled.")
            cap.read()
        ret, frame = cap.read()
        if not ret:
            return OperationResult(False, message="The camera did not return an image.")
        frame = cv2.flip(frame, 1)
    finally:
        cap.release()
        _notify_camera_state(camera_state_callback, "off")

    if cancel_event is not None and cancel_event.is_set():
        return OperationResult(False, message="Snapshot cancelled.")

    try:
        saved = cv2.imwrite(path, frame)
    except Exception as error:
        return OperationResult(False, message=f"Could not save {path}: {error}")
    if not saved:
        return OperationResult(False, message=f"Could not save {path}.")
    return OperationResult(True, value=path)


def _available_alert_sounds():
    """Return bundled alert sounds that are present on disk."""
    return [resource_path(path) for path in ALERT_SOUND_FILES if os.path.exists(resource_path(path))]


def play_alert(enabled=True):
    """Play a random posture alert clip."""
    if not enabled:
        print("Alert sound clips disabled")
        return False

    sounds = _available_alert_sounds()
    if not sounds:
        print("No alert sound clips found")
        return False

    sound_path = random.choice(sounds)
    threading.Thread(
        target=lambda: subprocess.run(["afplay", sound_path], check=False),
        daemon=True,
    ).start()
    return True


class FloatingPetPanel:
    def __init__(self):
        self.state = "good"
        self.window = None
        self.image_view = None
        self.bubble_view = None
        self.message_field = None

    def _build_panel(self):
        width = 338
        height = 112
        bubble_frame, image_frame = self._layout(height)
        x, y = self._default_origin(width, height)
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        self.window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, width, height),
            style,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.clearColor())
        self.window.setHasShadow_(True)
        self.window.setLevel_(NSFloatingWindowLevel)
        self.window.setHidesOnDeactivate_(False)
        self.window.setMovableByWindowBackground_(True)
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
        )

        self.bubble_view = DraggablePetBubbleView.alloc().initWithFrame_(bubble_frame)
        self.bubble_view.setWantsLayer_(True)
        self.bubble_view.refreshAppearance()
        self.bubble_view.layer().setCornerRadius_(12)
        self.bubble_view.layer().setMasksToBounds_(True)
        self.bubble_view.setAccessibilityLabel_("SpineSpy posture status")
        self.window.contentView().addSubview_(self.bubble_view)

        self.message_field = DraggablePetMessageField.alloc().initWithFrame_(
            self._message_frame(bubble_frame.size.width, bubble_frame.size.height)
        )
        self.message_field.setEditable_(False)
        self.message_field.setSelectable_(False)
        self.message_field.setBordered_(False)
        self.message_field.setBezeled_(False)
        self.message_field.setDrawsBackground_(False)
        self.message_field.setTextColor_(NSColor.labelColor())
        self.message_field.setFont_(NSFont.systemFontOfSize_(12))
        self.message_field.cell().setWraps_(False)
        self.message_field.cell().setScrollable_(False)
        self.message_field.setAccessibilityLabel_("Posture status")
        self.bubble_view.addSubview_(self.message_field)

        self.image_view = DraggablePetImageView.alloc().initWithFrame_(image_frame)
        self.image_view.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        self.window.contentView().addSubview_(self.image_view)

    def _layout(self, height):
        bubble_width, bubble_height = PET_BUBBLE_SIZE
        image_width = 96
        gap = 8
        margin = 8
        bubble_y = (height - bubble_height) / 2
        bubble_frame = NSMakeRect(margin, bubble_y, bubble_width, bubble_height)
        image_frame = NSMakeRect(margin + bubble_width + gap, 0, image_width, height)
        return bubble_frame, image_frame

    def _message_frame(self, bubble_width, bubble_height):
        horizontal_padding = 12
        vertical_padding = 9
        return NSMakeRect(
            horizontal_padding,
            vertical_padding - 1,
            bubble_width - (horizontal_padding * 2),
            bubble_height - (vertical_padding * 2) + 2,
        )

    def _default_origin(self, width, height):
        screen = NSScreen.mainScreen()
        if screen is None:
            return 80, 80
        frame = screen.visibleFrame()
        return frame.origin.x + frame.size.width - width - 28, frame.origin.y + frame.size.height - height - 28

    def set_state(self, state):
        self.state = state if state in {"good", "bad", "checking", "calibrating", "paused"} else "good"
        if self.image_view is not None:
            image_path = resource_path(PET_IMAGE_FILES.get(self.state, PET_IMAGE_FILES["good"]))
            self.image_view.setImage_(NSImage.alloc().initWithContentsOfFile_(image_path))
        if self.message_field is not None:
            message = PET_MESSAGES.get(self.state, PET_MESSAGES["good"])
            self.message_field.setStringValue_(message)
            self.message_field.setAccessibilityValue_(message)
            NSAccessibilityPostNotification(
                self.message_field,
                NSAccessibilityValueChangedNotification,
            )
            NSAccessibilityPostNotificationWithUserInfo(
                self.message_field,
                NSAccessibilityAnnouncementRequestedNotification,
                {
                    NSAccessibilityAnnouncementKey: message,
                    NSAccessibilityPriorityKey: NSAccessibilityPriorityMedium,
                },
            )

    def show(self):
        if self.window is None and NSPanel is not None:
            self._build_panel()
            self.set_state(self.state)
        if self.window is not None:
            self.window.orderFrontRegardless()


class PostureGuardApp(rumps.App):
    def __init__(self, settings_store=None, executor=None):
        global baseline_lean, baseline_tilt, effective_slouch_threshold, effective_tilt_threshold

        super().__init__(ICON_GOOD, quit_button=None)
        self.settings_store = settings_store or SettingsStore()
        settings = self.settings_store.load()
        if settings.calibration is not None:
            baseline_lean = settings.calibration.baseline_lean
            baseline_tilt = settings.calibration.baseline_tilt
            effective_slouch_threshold = settings.calibration.slouch_threshold
            effective_tilt_threshold = settings.calibration.tilt_threshold

        self.bad_streak = 0
        self.bad_reasons = []
        self.interval = settings.interval
        self.paused = False
        self.has_saved_calibration = settings.calibration is not None
        self.sound_clips_enabled = settings.sound_clips_enabled
        self.last_posture_state = "good"
        self.active_operation = None
        self._active_cancel_event = threading.Event()
        self._operations = OperationCoordinator()
        self._executor = executor or ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="SpineSpyWorker",
        )
        self._owns_executor = executor is None

        self.pet_panel = FloatingPetPanel()
        self.set_posture_state("good")
        rumps.events.before_start.register(self.pet_panel.show)
        if not self.has_saved_calibration:
            rumps.events.before_start.register(self._request_startup_calibration)

        self.monitoring_item = rumps.MenuItem("✓ Monitoring", callback=self.toggle_monitoring)
        sound_title = "✓ Sound Clips" if self.sound_clips_enabled else "Sound Clips (off)"
        self.sound_clips_item = rumps.MenuItem(sound_title, callback=self.toggle_sound_clips)
        self.camera_status_item = rumps.MenuItem("Camera: Off")

        self.interval_menu = rumps.MenuItem("Interval")
        self.interval_items = {
            30: rumps.MenuItem("30 seconds", callback=lambda _: self.set_interval(30)),
            60: rumps.MenuItem("1 minute", callback=lambda _: self.set_interval(60)),
            120: rumps.MenuItem("2 minutes", callback=lambda _: self.set_interval(120)),
            300: rumps.MenuItem("5 minutes", callback=lambda _: self.set_interval(300)),
        }
        for item in self.interval_items.values():
            self.interval_menu.add(item)
        self._update_interval_menu()

        self.settings_menu = rumps.MenuItem("Settings")
        self.settings_menu.add(self.sound_clips_item)

        self.menu = [
            self.monitoring_item,
            self.camera_status_item,
            self.interval_menu,
            self.settings_menu,
            None,
            rumps.MenuItem("Calibrate", callback=self.run_calibration),
            rumps.MenuItem("Save Snapshot", callback=self.save_snapshot),
            rumps.MenuItem("Test Alert", callback=lambda _: play_alert(self.sound_clips_enabled)),
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        self.timer = rumps.Timer(self.check_posture, self.interval)
        self.timer.start()

    @property
    def calibrating(self):
        return self.active_operation is Operation.CALIBRATING

    def _dispatch_main(self, callback, *args):
        AppHelper.callAfter(callback, *args)

    def set_posture_state(self, state):
        if state in {"good", "bad"}:
            self.last_posture_state = state
        self.pet_panel.set_state(state)
        self.title = {
            "good": ICON_GOOD,
            "bad": ICON_BAD,
            "checking": "📷",
            "calibrating": "📐",
            "paused": "💤",
        }.get(state, ICON_GOOD)

    def _render_current_state(self):
        self.set_posture_state("paused" if self.paused else self.last_posture_state)

    def _camera_state_changed(self, token, state):
        if not self._operations.accepts(token):
            return
        self.camera_status_item.title = {
            "opening": "Camera: Opening…",
            "on": "Camera: On • Capturing",
            "off": "Camera: Off • Processing locally",
        }.get(state, "Camera: Off")
        if state in {"opening", "on"} and self.active_operation is not Operation.CALIBRATING:
            self.set_posture_state("checking")

    def _camera_callback(self, token):
        return lambda state: self._dispatch_main(self._camera_state_changed, token, state)

    def _start_operation(self, operation, worker, completion):
        token = self._operations.reserve()
        if token is None:
            return False

        self.active_operation = operation
        self._active_cancel_event = threading.Event()
        if operation is Operation.CALIBRATING:
            self.set_posture_state("calibrating")
        else:
            self.set_posture_state("checking")

        try:
            future = self._executor.submit(
                worker,
                token,
                self._active_cancel_event,
            )
        except Exception as error:
            self._operations.finish(token)
            self.active_operation = None
            self._render_current_state()
            rumps.notification("SpineSpy", "Could not start operation", str(error))
            return False

        future.add_done_callback(
            lambda completed: self._operation_done(token, completion, completed)
        )
        return True

    def _operation_done(self, token, completion, future):
        try:
            result = future.result()
            if not isinstance(result, OperationResult):
                result = OperationResult(True, value=result)
        except Exception as error:
            result = OperationResult(False, message=str(error))
        self._dispatch_main(self._finish_operation, token, completion, result)

    def _finish_operation(self, token, completion, result):
        accepted = self._operations.finish(token)
        self.active_operation = None
        self.camera_status_item.title = "Camera: Off"
        if not accepted:
            self._render_current_state()
            return
        completion(result)

    def _save_settings(self):
        calibration = None
        if self.has_saved_calibration:
            calibration = CalibrationSettings(
                baseline_lean=baseline_lean,
                baseline_tilt=baseline_tilt,
                slouch_threshold=effective_slouch_threshold,
                tilt_threshold=effective_tilt_threshold,
            )
        try:
            self.settings_store.save(
                AppSettings(
                    interval=self.interval,
                    sound_clips_enabled=self.sound_clips_enabled,
                    calibration=calibration,
                )
            )
        except OSError as error:
            print(f"Could not save settings: {error}")

    def _update_interval_menu(self):
        labels = {30: "30 seconds", 60: "1 minute", 120: "2 minutes", 300: "5 minutes"}
        for seconds, item in self.interval_items.items():
            prefix = "✓ " if seconds == self.interval else ""
            item.title = f"{prefix}{labels[seconds]}"

    def _request_startup_calibration(self):
        self._request_calibration(startup=True)

    def run_calibration(self, _):
        self._request_calibration(startup=False)

    def _request_calibration(self, startup):
        title = "Starting up" if startup else "Calibration starting"
        message = (
            "Sit with good posture. Auto-calibrating in 3 seconds..."
            if startup
            else "Sit in your best posture. Calibration begins in 3 seconds..."
        )
        failure_message = (
            "Could not detect your pose. Make sure you're visible and well-lit."
            if startup
            else "Could not detect your pose in enough frames. Make sure you're visible and well-lit."
        )

        def worker(token, cancel_event):
            if cancel_event.wait(3):
                return OperationResult(False, message="Calibration cancelled.")
            calibrated = calibrate(
                camera_state_callback=self._camera_callback(token),
                cancel_event=cancel_event,
            )
            return OperationResult(calibrated, message=failure_message)

        if self._start_operation(
            Operation.CALIBRATING,
            worker,
            self._complete_calibration,
        ):
            rumps.notification("SpineSpy", title, message)

    def _complete_calibration(self, result):
        if result.succeeded:
            self.has_saved_calibration = True
            self._save_settings()
            rumps.notification(
                "SpineSpy",
                "Calibration complete",
                "Your good posture baseline has been captured.",
            )
        else:
            rumps.notification("SpineSpy", "Calibration failed", result.message)
        self._render_current_state()

    def check_posture(self, _):
        if self.paused:
            return

        def worker(token, cancel_event):
            value = take_snapshot(
                camera_state_callback=self._camera_callback(token),
                cancel_event=cancel_event,
            )
            return OperationResult(True, value=value)

        self._start_operation(
            Operation.MONITORING,
            worker,
            self._complete_monitoring,
        )

    def _complete_monitoring(self, result):
        if not result.succeeded:
            rumps.notification("SpineSpy", "Posture check failed", result.message)
            self._render_current_state()
            return

        is_bad, reason = result.value
        if is_bad is None:
            if reason != "Cancelled":
                print(f"Error: {reason}")
            self._render_current_state()
            return

        if is_bad:
            self.bad_streak += 1
            self.bad_reasons.append(reason)
            self.set_posture_state("bad")
            print(f"Bad: {reason} (streak: {self.bad_streak}/{BAD_STREAK_LIMIT})")
            if self.bad_streak >= BAD_STREAK_LIMIT:
                reason_counts = Counter(self.bad_reasons)
                dominant, count = reason_counts.most_common(1)[0]
                print(f"Alert: {dominant} detected {count}/{self.bad_streak} checks")
                play_alert(self.sound_clips_enabled)
                self.bad_streak = 0
                self.bad_reasons = []
        else:
            self.bad_streak = 0
            self.bad_reasons = []
            self.set_posture_state("good")
            print("Good posture")

    def _choose_snapshot_path(self):
        application = NSApplication.sharedApplication()
        application.activateIgnoringOtherApps_(True)
        panel = NSSavePanel.savePanel()
        panel.setTitle_("Save SpineSpy Snapshot")
        panel.setNameFieldStringValue_("SpineSpy Snapshot.jpg")
        panel.setAllowedContentTypes_([UTTypeJPEG, UTTypePNG])
        panel.setAllowsOtherFileTypes_(False)
        if panel.runModal() != NSModalResponseOK:
            return None
        path = str(panel.URL().path())
        if not os.path.splitext(path)[1]:
            path = f"{path}.jpg"
        return path

    def save_snapshot(self, _):
        path = self._choose_snapshot_path()
        if path is None:
            return

        def worker(token, cancel_event):
            return save_camera_frame(
                path,
                camera_state_callback=self._camera_callback(token),
                cancel_event=cancel_event,
            )

        self._start_operation(
            Operation.SAVING,
            worker,
            self._complete_snapshot_save,
        )

    def _complete_snapshot_save(self, result):
        if result.succeeded:
            rumps.notification(
                "SpineSpy",
                "Snapshot saved",
                f"Saved to {result.value}",
            )
        else:
            rumps.notification("SpineSpy", "Snapshot failed", result.message)
        self._render_current_state()

    def toggle_monitoring(self, sender):
        self.paused = not self.paused
        sender.title = "Monitoring (paused)" if self.paused else "✓ Monitoring"
        if self.paused:
            self._operations.invalidate_result()
            self._active_cancel_event.set()
        self._render_current_state()

    def toggle_sound_clips(self, sender):
        self.sound_clips_enabled = not self.sound_clips_enabled
        sender.title = "✓ Sound Clips" if self.sound_clips_enabled else "Sound Clips (off)"
        self._save_settings()

    def set_interval(self, seconds):
        self.interval = seconds
        self.timer.stop()
        self.timer = rumps.Timer(self.check_posture, self.interval)
        self.timer.start()
        self._update_interval_menu()
        self._save_settings()
        print(f"Interval set to {seconds}s")

    def quit_app(self, _):
        self._operations.begin_shutdown()
        self._active_cancel_event.set()
        self.timer.stop()
        self._executor.shutdown(wait=True, cancel_futures=True)
        close_detectors()
        rumps.quit_application()


def main():
    """CLI/script entrypoint."""
    if os.environ.get("SPINESPY_IMPORT_SMOKE_TEST") == "1":
        return
    PostureGuardApp().run()


if __name__ == "__main__":
    main()

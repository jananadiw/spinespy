import rumps
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from ultralytics import YOLO
import os
import sys
import time
import threading
import urllib.request


def resource_path(relative_path):
    """Get path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return relative_path


# Icons
ICON_GOOD = "🦸"
ICON_BAD = "🧟"

# Detection config
SLOUCH_THRESHOLD = 0.1
TILT_THRESHOLD = 0.05
BAD_STREAK_LIMIT = 5

# Calibration baseline (set via calibrate())
baseline_lean = 0.0
baseline_tilt = 0.0

# Download pose model if needed
MODEL_PATH = resource_path("pose_landmarker.task")
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"

if not os.path.exists(MODEL_PATH):
    print("Downloading pose model...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

# MediaPipe setup (new API)
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.PoseLandmarkerOptions(base_options=base_options, output_segmentation_masks=False)
pose_detector = vision.PoseLandmarker.create_from_options(options)

# YOLO setup
yolo = YOLO(resource_path("yolo26s.pt"))
PHONE_CLASS_ID = 67


def camera_permission_hint():
    """Return an actionable camera-access hint for the current platform."""
    if sys.platform == "darwin":
        return (
            "macOS likely blocked camera access. Enable it in System Settings > Privacy & Security > "
            "Camera for the exact app/process running SpineSpy (Terminal, iTerm, Python, or SpineSpy.app)."
        )
    return "Camera is unavailable, already in use by another app, or not permitted."


def get_posture_metrics(landmarks):
    """Extract forward lean and tilt from landmarks."""
    nose = landmarks[0]
    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]

    shoulder_z = (left_shoulder.z + right_shoulder.z) / 2
    forward_lean = shoulder_z - nose.z
    tilt = abs(left_shoulder.y - right_shoulder.y)
    return forward_lean, tilt


def calibrate():
    """Capture current posture as the baseline."""
    global baseline_lean, baseline_tilt
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"Calibration failed: camera error. {camera_permission_hint()}")
        return False

    time.sleep(0.5)
    for _ in range(5):
        cap.read()

    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("Calibration failed: capture error")
        return False

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    results = pose_detector.detect(mp_image)

    if results.pose_landmarks and len(results.pose_landmarks) > 0:
        lean, tilt = get_posture_metrics(results.pose_landmarks[0])
        baseline_lean = lean
        baseline_tilt = tilt
        print(f"✓ Calibrated: baseline_lean={baseline_lean:.3f}, baseline_tilt={baseline_tilt:.3f}")
        return True

    print("Calibration failed: no pose detected")
    return False


def check_posture(landmarks):
    """Check for slouching and side tilt relative to calibrated baseline."""
    forward_lean, tilt = get_posture_metrics(landmarks)
    lean_delta = forward_lean - baseline_lean
    tilt_delta = tilt - baseline_tilt

    print(f"  [DEBUG] lean_delta={lean_delta:.3f} (threshold={SLOUCH_THRESHOLD}), tilt_delta={tilt_delta:.3f} (threshold={TILT_THRESHOLD})")

    if lean_delta >= SLOUCH_THRESHOLD:
        return True, "Slouching"
    if tilt_delta >= TILT_THRESHOLD:
        return True, "Tilting"
    return False, None


def detect_phone(frame):
    """Detect phone in frame."""
    results = yolo(frame, verbose=False)
    for r in results:
        for box in r.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            print(f"  [DEBUG] Detected class_id={class_id}, confidence={confidence:.2f}")
            if class_id == PHONE_CLASS_ID:
                print(f"  [DEBUG] ✓ Phone detected! (class {PHONE_CLASS_ID})")
                return True
    print(f"  [DEBUG] No phone detected (looking for class {PHONE_CLASS_ID})")
    return False


def take_snapshot(save_debug=False):
    """Capture single frame, analyze, return result."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"Snapshot failed: camera error. {camera_permission_hint()}")
        return None, "Camera error"

    time.sleep(0.5)
    for _ in range(5):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret:
        return None, "Capture failed"

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    if save_debug:
        cv2.imwrite("debug_snapshot.jpg", frame)
        print("Saved debug_snapshot.jpg")

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    pose_results = pose_detector.detect(mp_image)

    print(f"[DEBUG] Pose detected: {len(pose_results.pose_landmarks) if pose_results.pose_landmarks else 0} people")

    if pose_results.pose_landmarks and len(pose_results.pose_landmarks) > 0:
        posture_bad, reason = check_posture(pose_results.pose_landmarks[0])
        if posture_bad:
            return True, reason

    phone_found = detect_phone(frame)
    print(f"[DEBUG] Phone detected: {phone_found}")

    if phone_found:
        return True, "Phone detected"

    return False, "Good posture"


def play_alert():
    """Play system alert sound."""
    threading.Thread(
        target=lambda: os.system("afplay /System/Library/Sounds/Glass.aiff"),
        daemon=True,
    ).start()


class PostureGuardApp(rumps.App):
    def __init__(self):
        super().__init__(ICON_GOOD, quit_button=None)
        self.bad_streak = 0
        self.interval = 60
        self.paused = False

        self.monitoring_item = rumps.MenuItem("✓ Monitoring", callback=self.toggle_monitoring)

        self.interval_menu = rumps.MenuItem("Interval")
        self.interval_menu.add(rumps.MenuItem("30 seconds", callback=lambda _: self.set_interval(30)))
        self.interval_menu.add(rumps.MenuItem("1 minute", callback=lambda _: self.set_interval(60)))
        self.interval_menu.add(rumps.MenuItem("2 minutes", callback=lambda _: self.set_interval(120)))
        self.interval_menu.add(rumps.MenuItem("5 minutes", callback=lambda _: self.set_interval(300)))

        self.menu = [
            self.monitoring_item,
            self.interval_menu,
            None,
            rumps.MenuItem("Calibrate", callback=self.run_calibration),
            rumps.MenuItem("Save Snapshot", callback=lambda _: take_snapshot(save_debug=True)),
            rumps.MenuItem("Test Alert", callback=lambda _: play_alert()),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

        self.timer = rumps.Timer(self.check_posture, self.interval)
        self.timer.start()

        # Auto-calibrate on startup
        threading.Thread(target=calibrate, daemon=True).start()

    def run_calibration(self, _):
        threading.Thread(target=self._calibrate_with_feedback, daemon=True).start()

    def _calibrate_with_feedback(self):
        if calibrate():
            rumps.notification("SpineSpy", "Calibration complete", "Your good posture has been saved as baseline.")
        else:
            rumps.notification("SpineSpy", "Calibration failed", "Make sure you're visible to the camera.")

    def check_posture(self, _):
        if self.paused:
            return

        is_bad, reason = take_snapshot()

        if is_bad is None:
            print(f"Error: {reason}")
            return

        if is_bad:
            self.bad_streak += 1
            self.title = ICON_BAD
            print(f"Bad: {reason} (streak: {self.bad_streak}/{BAD_STREAK_LIMIT})")

            if self.bad_streak >= BAD_STREAK_LIMIT:
                play_alert()
                self.bad_streak = 0
        else:
            self.bad_streak = 0
            self.title = ICON_GOOD
            print("Good posture")

    def toggle_monitoring(self, sender):
        self.paused = not self.paused
        sender.title = "Monitoring (paused)" if self.paused else "✓ Monitoring"

    def set_interval(self, seconds):
        self.interval = seconds
        self.timer.stop()
        self.timer = rumps.Timer(self.check_posture, self.interval)
        self.timer.start()
        print(f"Interval set to {seconds}s")


def main():
    """CLI/script entrypoint."""
    PostureGuardApp().run()


if __name__ == "__main__":
    main()

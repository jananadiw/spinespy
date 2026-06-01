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
import statistics
import random
import subprocess
from collections import Counter


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

# Alert audio clips
ALERT_SOUND_FILES = [
    "audio/Come on, shoulders back.mp3",
    "audio/auditioning to be a shrimp.mp3",
    "audio/did gravity offend u.mp3",
    "audio/slouching_bella.mp3",
    "audio/writing in cursive.mp3",
    "audio/you're not a croissant.mp3",
]

# Calibration config
CALIBRATION_FRAMES = 10
CALIBRATION_INTERVAL = 0.3

# Calibration baseline (set via calibrate())
baseline_lean = 0.0
baseline_tilt = 0.0
effective_slouch_threshold = SLOUCH_THRESHOLD
effective_tilt_threshold = TILT_THRESHOLD

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
    """Capture multiple frames and compute a robust baseline from median metrics."""
    global baseline_lean, baseline_tilt, effective_slouch_threshold, effective_tilt_threshold
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"Calibration failed: camera error. {camera_permission_hint()}")
        return False

    time.sleep(0.5)
    for _ in range(5):
        cap.read()

    leans = []
    tilts = []
    for _ in range(CALIBRATION_FRAMES):
        ret, frame = cap.read()
        if not ret:
            continue
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = pose_detector.detect(mp_image)
        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            lean, tilt = get_posture_metrics(results.pose_landmarks[0])
            leans.append(lean)
            tilts.append(tilt)
        time.sleep(CALIBRATION_INTERVAL)

    cap.release()

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


SNAPSHOT_FRAMES = 3


def take_snapshot(save_debug=False):
    """Capture multiple frames, analyze with majority voting, return result."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"Snapshot failed: camera error. {camera_permission_hint()}")
        return None, "Camera error"

    time.sleep(0.5)
    for _ in range(5):
        cap.read()

    frames = []
    for _ in range(SNAPSHOT_FRAMES):
        ret, frame = cap.read()
        if ret:
            frames.append(cv2.flip(frame, 1))
    cap.release()

    if not frames:
        return None, "Capture failed"

    if save_debug:
        cv2.imwrite("debug_snapshot.jpg", frames[-1])
        print("Saved debug_snapshot.jpg")

    bad_votes = []
    reasons = []
    for frame in frames:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        pose_results = pose_detector.detect(mp_image)

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


class PostureGuardApp(rumps.App):
    def __init__(self):
        super().__init__(ICON_GOOD, quit_button=None)
        self.bad_streak = 0
        self.bad_reasons = []
        self.interval = 60
        self.paused = False
        self.calibrating = False
        self.sound_clips_enabled = True

        self.monitoring_item = rumps.MenuItem("✓ Monitoring", callback=self.toggle_monitoring)
        self.sound_clips_item = rumps.MenuItem("✓ Sound Clips", callback=self.toggle_sound_clips)

        self.interval_menu = rumps.MenuItem("Interval")
        self.interval_menu.add(rumps.MenuItem("30 seconds", callback=lambda _: self.set_interval(30)))
        self.interval_menu.add(rumps.MenuItem("1 minute", callback=lambda _: self.set_interval(60)))
        self.interval_menu.add(rumps.MenuItem("2 minutes", callback=lambda _: self.set_interval(120)))
        self.interval_menu.add(rumps.MenuItem("5 minutes", callback=lambda _: self.set_interval(300)))

        self.settings_menu = rumps.MenuItem("Settings")
        self.settings_menu.add(self.sound_clips_item)

        self.menu = [
            self.monitoring_item,
            self.interval_menu,
            self.settings_menu,
            None,
            rumps.MenuItem("Calibrate", callback=self.run_calibration),
            rumps.MenuItem("Save Snapshot", callback=lambda _: take_snapshot(save_debug=True)),
            rumps.MenuItem("Test Alert", callback=lambda _: play_alert(self.sound_clips_enabled)),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

        self.timer = rumps.Timer(self.check_posture, self.interval)
        self.timer.start()

        threading.Thread(target=self._startup_calibration, daemon=True).start()

    def _startup_calibration(self):
        rumps.notification("SpineSpy", "Starting up", "Sit with good posture. Auto-calibrating in 3 seconds...")
        time.sleep(3)
        self.calibrating = True
        self.title = "📐"
        try:
            if calibrate():
                rumps.notification("SpineSpy", "Calibration complete", "Your good posture baseline has been captured.")
            else:
                rumps.notification("SpineSpy", "Calibration failed", "Could not detect your pose. Make sure you're visible and well-lit.")
        finally:
            self.calibrating = False
            self.title = ICON_GOOD

    def run_calibration(self, _):
        threading.Thread(target=self._calibrate_with_feedback, daemon=True).start()

    def _calibrate_with_feedback(self):
        rumps.notification("SpineSpy", "Calibration starting", "Sit in your best posture. Calibration begins in 3 seconds...")
        time.sleep(3)
        self.calibrating = True
        self.title = "📐"
        try:
            if calibrate():
                rumps.notification("SpineSpy", "Calibration complete", "Your good posture baseline has been captured.")
            else:
                rumps.notification("SpineSpy", "Calibration failed", "Could not detect your pose in enough frames. Make sure you're visible and well-lit.")
        finally:
            self.calibrating = False
            self.title = ICON_GOOD

    def check_posture(self, _):
        if self.paused or self.calibrating:
            return

        is_bad, reason = take_snapshot()

        if is_bad is None:
            print(f"Error: {reason}")
            return

        if is_bad:
            self.bad_streak += 1
            self.bad_reasons.append(reason)
            self.title = ICON_BAD
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
            self.title = ICON_GOOD
            print("Good posture")

    def toggle_monitoring(self, sender):
        self.paused = not self.paused
        sender.title = "Monitoring (paused)" if self.paused else "✓ Monitoring"

    def toggle_sound_clips(self, sender):
        self.sound_clips_enabled = not self.sound_clips_enabled
        sender.title = "✓ Sound Clips" if self.sound_clips_enabled else "Sound Clips (off)"

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

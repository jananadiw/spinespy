import rumps
import cv2
import mediapipe as mp
from ultralytics import YOLO
import os
import threading

# Detection config
SLOUCH_THRESHOLD = 0.1
TILT_THRESHOLD = 0.05
BAD_STREAK_LIMIT = 5

# MediaPipe setup
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# YOLO setup
yolo = YOLO("yolov8n.pt")
PHONE_CLASS_ID = 67


def check_posture(landmarks):
    """Check for slouching and side tilt."""
    nose = landmarks[mp_pose.PoseLandmark.NOSE]
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    
    shoulder_z = (left_shoulder.z + right_shoulder.z) / 2
    forward_lean = shoulder_z - nose.z
    tilt = abs(left_shoulder.y - right_shoulder.y)
    
    if forward_lean > SLOUCH_THRESHOLD:
        return True, "Slouching"
    if tilt > TILT_THRESHOLD:
        return True, "Tilting"
    return False, None


def detect_phone(frame):
    """Detect phone in frame."""
    results = yolo(frame, verbose=False)
    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == PHONE_CLASS_ID:
                return True
    return False


def take_snapshot():
    """Capture single frame, analyze, return result."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return None, "Camera error"
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return None, "Capture failed"
    
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Check posture
    pose_results = pose.process(rgb)
    if pose_results.pose_landmarks:
        posture_bad, reason = check_posture(pose_results.pose_landmarks.landmark)
        if posture_bad:
            return True, reason
    
    # Check phone
    if detect_phone(frame):
        return True, "Phone detected"
    
    return False, "Good posture"


def play_alert():
    """Play system alert sound."""
    threading.Thread(
        target=lambda: os.system("afplay /System/Library/Sounds/Sosumi.aiff"),
        daemon=True
    ).start()


class PostureGuardApp(rumps.App):
    def __init__(self):
        super().__init__("🟢", quit_button=None)
        self.bad_streak = 0
        self.interval = 60
        self.paused = False
        
        # Menu items
        self.monitoring_item = rumps.MenuItem("✓ Monitoring", callback=self.toggle_monitoring)
        self.menu = [
            self.monitoring_item,
            rumps.MenuItem("Interval", [
                rumps.MenuItem("30 seconds", callback=lambda _: self.set_interval(30)),
                rumps.MenuItem("1 minute", callback=lambda _: self.set_interval(60)),
                rumps.MenuItem("2 minutes", callback=lambda _: self.set_interval(120)),
                rumps.MenuItem("5 minutes", callback=lambda _: self.set_interval(300)),
            ]),
            None,
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]
        
        # Start timer
        self.timer = rumps.Timer(self.check_posture, self.interval)
        self.timer.start()
    
    def check_posture(self, _):
        if self.paused:
            return
        
        is_bad, reason = take_snapshot()
        
        if is_bad is None:
            print(f"Error: {reason}")
            return
        
        if is_bad:
            self.bad_streak += 1
            self.title = "🔴"
            print(f"Bad: {reason} (streak: {self.bad_streak}/{BAD_STREAK_LIMIT})")
            
            if self.bad_streak >= BAD_STREAK_LIMIT:
                play_alert()
                self.bad_streak = 0
        else:
            self.bad_streak = 0
            self.title = "🟢"
            print("Good posture")
    
    def toggle_monitoring(self, sender):
        self.paused = not self.paused
        sender.title = "Monitoring (paused)" if self.paused else "✓ Monitoring"
        self.title = "⏸️" if self.paused else "🟢"
    
    def set_interval(self, seconds):
        self.interval = seconds
        self.timer.stop()
        self.timer = rumps.Timer(self.check_posture, self.interval)
        self.timer.start()
        print(f"Interval set to {seconds}s")


if __name__ == "__main__":
    PostureGuardApp().run()

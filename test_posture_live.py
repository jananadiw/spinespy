#!/usr/bin/env python3
"""Live posture detection test with visual overlay."""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import os
import urllib.request

from menubar_app import SLOUCH_THRESHOLD, TILT_THRESHOLD, check_posture, get_posture_metrics, calibrate, baseline_lean, baseline_tilt

# Download pose model if needed
MODEL_PATH = "pose_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading pose model...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

# Key landmark indices
NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12

# Pose connections to draw skeleton
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),  # face right
    (0, 4), (4, 5), (5, 6), (6, 8),  # face left
    (11, 12),  # shoulders
    (11, 13), (13, 15),  # left arm
    (12, 14), (14, 16),  # right arm
    (11, 23), (12, 24),  # torso
    (23, 24),  # hips
    (23, 25), (25, 27),  # left leg
    (24, 26), (26, 28),  # right leg
]


def main():
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(base_options=base_options, output_segmentation_masks=False)
    pose_detector = vision.PoseLandmarker.create_from_options(options)

    print("Opening camera...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera")
        return 1

    print("✓ Camera opened")
    print("\nPress 'c' to calibrate your good posture first!")
    print("Then try slouching or tilting to see detection")
    print("Press 'q' to quit, 's' to save snapshot\n")

    time.sleep(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = pose_detector.detect(mp_image)

        status = "No person detected"
        color = (128, 128, 128)
        lean_delta = 0.0
        tilt_delta = 0.0

        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            landmarks = results.pose_landmarks[0]

            # Draw skeleton
            for c in CONNECTIONS:
                if c[0] < len(landmarks) and c[1] < len(landmarks):
                    pt1 = (int(landmarks[c[0]].x * w), int(landmarks[c[0]].y * h))
                    pt2 = (int(landmarks[c[1]].x * w), int(landmarks[c[1]].y * h))
                    cv2.line(frame, pt1, pt2, (255, 200, 0), 2)

            # Draw key landmarks
            for idx in [NOSE, LEFT_SHOULDER, RIGHT_SHOULDER]:
                lm = landmarks[idx]
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (cx, cy), 6, (0, 255, 255), -1)

            # Compute posture metrics
            forward_lean, tilt = get_posture_metrics(landmarks)

            import menubar_app
            lean_delta = forward_lean - menubar_app.baseline_lean
            tilt_delta = tilt - menubar_app.baseline_tilt

            is_bad, reason = check_posture(landmarks)
            if is_bad:
                status = f"BAD: {reason}"
                color = (0, 0, 255)
            else:
                status = "Good posture"
                color = (0, 255, 0)

        # Draw overlay
        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        import menubar_app
        cv2.putText(
            frame,
            f"Lean delta: {lean_delta:.3f} (thresh: {SLOUCH_THRESHOLD}) | baseline: {menubar_app.baseline_lean:.3f}",
            (10, h - 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            f"Tilt delta: {tilt_delta:.3f} (thresh: {TILT_THRESHOLD}) | baseline: {menubar_app.baseline_tilt:.3f}",
            (10, h - 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        cv2.imshow("Posture Detection Test", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("c"):
            calibrate()
            print("✓ Baseline set! Now try slouching or tilting.")
        if key == ord("s"):
            filename = f"test_posture_{int(time.time())}.jpg"
            cv2.imwrite(filename, frame)
            print(f"💾 Saved {filename}")

    cap.release()
    cv2.destroyAllWindows()
    print("\n✓ Test complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

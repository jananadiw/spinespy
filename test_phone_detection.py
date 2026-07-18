#!/usr/bin/env python3
"""Test phone detection with live camera feed."""

import cv2
import time

from menubar_app import get_phone_detections


def main():
    print("Opening camera...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Cannot open camera")
        return 1

    print("✓ Camera opened")
    print("\n📱 Hold your phone in front of the camera")
    print("Press 'q' to quit, 's' to save snapshot\n")

    time.sleep(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to grab frame")
            break

        phone_detected = False
        for detection in get_phone_detections(frame):
            if not detection.categories:
                continue
            category = detection.categories[0]
            box = detection.bounding_box
            x1, y1 = box.origin_x, box.origin_y
            x2, y2 = x1 + box.width, y1 + box.height
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"cell phone {category.score:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )
            phone_detected = True
            print(f"✓ Phone detected! Confidence: {category.score:.2f}")

        # Show status
        status = "📱 PHONE DETECTED" if phone_detected else "No phone"
        color = (0, 255, 0) if phone_detected else (0, 0, 255)
        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.imshow("Phone Detection Test", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            filename = f"test_snapshot_{int(time.time())}.jpg"
            cv2.imwrite(filename, frame)
            print(f"💾 Saved {filename}")

    cap.release()
    cv2.destroyAllWindows()
    print("\n✓ Test complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

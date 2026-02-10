#!/usr/bin/env python3
"""Test phone detection with live camera feed."""

import cv2
from ultralytics import YOLO
import time

print("Loading YOLO model...")
yolo = YOLO("yolo26s.pt")
PHONE_CLASS_ID = 67

print("Opening camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Cannot open camera")
    exit(1)

print("✓ Camera opened")
print("\n📱 Hold your phone in front of the camera")
print("Press 'q' to quit, 's' to save snapshot\n")

time.sleep(1)

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to grab frame")
        break
    
    # Run detection
    results = yolo(frame, verbose=False)
    
    phone_detected = False
    for r in results:
        for box in r.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = yolo.names[class_id]
            
            # Draw all detections
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            color = (0, 255, 0) if class_id == PHONE_CLASS_ID else (255, 0, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{class_name} {confidence:.2f}", 
                       (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            if class_id == PHONE_CLASS_ID:
                phone_detected = True
                print(f"✓ Phone detected! Confidence: {confidence:.2f}")
    
    # Show status
    status = "📱 PHONE DETECTED" if phone_detected else "No phone"
    color = (0, 255, 0) if phone_detected else (0, 0, 255)
    cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    cv2.imshow('Phone Detection Test', frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        filename = f"test_snapshot_{int(time.time())}.jpg"
        cv2.imwrite(filename, frame)
        print(f"💾 Saved {filename}")

cap.release()
cv2.destroyAllWindows()
print("\n✓ Test complete")

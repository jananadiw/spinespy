# SpineSpy 1.2.5

This release makes scheduled camera checks easier to understand and stop
without opening the app.

## Predictable captures

- Shows the exact local time of the next scheduled capture in the menu.
- Puts **Pause Monitoring** at the top of the menu and changes it to
  **Resume Monitoring** while paused.
- Stops the capture timer while paused and schedules the next capture one full
  interval after monitoring resumes.
- Reschedules the displayed capture time immediately when the interval changes.

## Accurate camera state

- Shows the 📷 menu-bar indicator only while the camera is opening or active,
  including during calibration and manual snapshots.
- Restores the posture or calibration icon as soon as the camera closes, while
  the menu continues to say that processing is local.
- Cancels an active capture when monitoring is paused and ignores stale results.

Camera frames remain in memory and are discarded after analysis unless the user
explicitly selects **Save Snapshot**.

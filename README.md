# Fly Swat

Examples:

- `simple_webcam_capture.py`: webcam capture.
- `mediapipe_handtracking.py`: hand tracking.
- `fly_overlay_example.py`: fly (animated circle) moving over the webcam feed. Press `q` to quit.
- `src/fly_swat/game.py`: fly movement physics and capture rule, independent of the camera.
- `src/fly_swat/gestures.py`: pinch detection (hysteresis, debouncing) and active hand selection.
- `src/fly_swat/vision.py`: webcam and MediaPipe hand landmark extraction.
- `pinch_debug.py`: shows thumb/index tips, pinch state (OPEN/CLOSED), thresholds and the capture overlay. Keys: `q` quit, `a`/`z` close threshold, `s`/`x` open threshold, `g` toggle fly, `[`/`]` fly speed, `f` freeze fly.

    uv run fly_overlay_example.py
    uv run pinch_debug.py

Tests:

    uv run python -m unittest discover -s tests

See `docs/flyswat_pinch_plan.md` for the implementation plan.

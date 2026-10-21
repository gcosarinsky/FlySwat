# Pinch detection and fly interaction: implementation plan

Date: 2026-10-21 15:34 (UTC+02:00)

Related documents:

- [Hand selection](./flyswat_seleccion_de_mano.md)
- [Public repo architecture](./fly_swat_repo_publico_arquitectura.md)

## Current state

- Fly physics lives in `src/fly_swat/game.py` (`Fly`), independent of the camera.
- `mediapipe_handtracking.py` is a standalone example that uses `num_hands=2` but is not connected to the game.
- There is no pinch detection, no hand selection and no capture rule yet.
- `fly_overlay_example.py` shows the fly over the webcam feed.

## MVP design

```text
webcam -> detect up to 2 hands -> pinch state per hand
       -> select one active hand -> interaction with the fly -> capture event
```

Detection and game logic stay independent of OpenCV and MediaPipe so the interaction can be tested without a webcam. The MVP uses a single active hand, as decided in the hand selection document.

## Phases

### 1. Hand and pinch data

Per detected hand, define a state with at least:

- Interaction point: midpoint between the thumb tip (landmark 4) and the index tip (landmark 8).
- Pinch state: open or closed.
- Distance between the tips, for diagnostics and visualization.
- Optionally, detection confidence and the `Left`/`Right` label, for display only. The label is **not** a persistent identity.

Convert normalized MediaPipe coordinates to pixels in a single layer, matching the mirrored image the player sees and the fly's coordinate space.

**Acceptance:** with one detected hand, the interaction point is drawn where expected and matches the game coordinate space.

### 2. Stable pinch detection

- Compare the tip distance against a hand-relative measure (for example palm width), not a fixed pixel value, so it works at different camera distances.
- **Hysteresis:** one threshold to close the pinch and a wider one to reopen it.
- **Temporal stability:** a state change must persist for a few frames or milliseconds.
- Expose thresholds as documented, configurable constants. No magic values scattered in the code.

**Acceptance:** a still hand near the threshold does not flicker between open and closed, and the gesture responds when closing and when opening.

### 2b. Pinch debug script (`pinch_debug.py`)

A script next to the other examples that reuses the same `vision.py` and `gestures.py` code as the game, so what it shows is what the game evaluates, with no duplicated logic.

Per detected hand it shows:

- Thumb and index tips as highlighted circles joined by a line.
- The interaction point (midpoint) marker.
- The pinch state, as color (green = closed, red = open) and a text label (`OPEN` / `CLOSED`).
- Current normalized distance, the close/open thresholds and the hand reference measure.
- Hand index in the frame, `Left`/`Right` label and confidence (informational only).

Global information:

- FPS and number of detected hands.
- Pending state changes (temporal stability not yet confirmed).
- A bar showing the distance between the close and open thresholds.

Optional, enabled as later phases land:

- Highlight the active hand and why it was chosen (phase 3).
- Draw the fly, its capture radius and whether the interaction point is inside it (phase 4).
- Capture counter and a notice when a capture event occurs.

Controls:

- `q` quits.
- Keys to toggle layers (for example all landmarks) and, optionally, adjust thresholds live for calibration.
- Command-line arguments for the model path and camera index. The default model path is relative to the repository.

Design requirements:

- Draw on the already mirrored image, using the same pixel coordinates the game uses.
- Keep drawing (OpenCV) separate from pinch logic. The script only consumes the computed state.
- Release the camera and detector on errors. Show a clear message if there is no camera or the model is missing.
- All UI text in English.

Manual verification:

1. An open hand shows `OPEN`.
2. Joining the fingers switches to `CLOSED` without flicker.
3. Holding the fingers near the threshold does not oscillate (hysteresis).
4. Moving the hand toward or away from the camera behaves consistently (relative threshold).
5. With two hands, each shows its own independent state.

### 3. Active hand selection

Deterministic selection so only one hand controls the game even if two are detected:

1. If only one hand is pinching, select it.
2. If both pinch, select the one whose pinch point is closest to the fly.
3. If none pinch, keep the previous active hand while it is still detected.
4. If there is no valid previous hand, select the hand closest to the fly.
5. Apply a small temporal hysteresis before switching between hands.

Per-frame detections are new objects, so keep the logical identity of a hand through spatial continuity (smallest distance between interaction points in consecutive frames), not object comparison and not the `Left`/`Right` label.

**Acceptance:** with two hands in view, control does not jump between them on small movements or label changes, and a single pinching hand takes priority.

### 4. Capture rule in the game core

A capture happens when both hold:

- The active hand's pinch **closes** (open -> closed transition), not merely "is closed".
- Its interaction point is within the capture radius around the fly center at that moment.

- The capture radius is a game parameter, related to the fly's visual radius plus a user tolerance.
- The core reports the capture as an event. It does not draw or read the camera.
- A pinch that was already closed when the fly came close does not count; it must be released and closed again. This also prevents repeated captures while the pinch is held, and a newly selected hand cannot capture on its first frame.
- `Fly.step` keeps handling movement. The interaction must not depend on OpenCV or MediaPipe.

**Acceptance:** an open pinch, a pinch outside the radius, or a pinch already closed before reaching the fly does not capture; closing the pinch inside the radius produces exactly one capture event.

### 5. Integration

Small modules, following the suggested architecture:

- `vision.py`: camera, MediaPipe and landmark extraction.
- `gestures.py`: pinch state and active hand selection.
- `game.py`: physics, capture rule and events.
- `app.py` (or the game example): wiring and rendering.

While integrating:

- Use the model stored in the repository (`models/hand_landmarker.task`), not an absolute path from another machine.
- Compute frame time with a monotonic clock.
- Release the camera and detector on errors and on exit.

**Acceptance:** the user can play with the webcam and exit cleanly; vision and game modules keep separate responsibilities.

### 6. Tests and verification

Automated tests (no camera), extending `tests/test_game.py`:

- Close/open thresholds, including hysteresis.
- Temporal stability against fluctuating measurements.
- Hand selection with zero, one and two pinching hands.
- Active hand persistence and controlled switching when it disappears.
- Capture inside and outside the radius, and no repeated captures while the pinch is held.

Manual webcam validation: one and two hands, different camera distances, fast movements, held pinch and release.

## Work order

1. Define hand and game data structures.
2. Implement stable pinch detection and test it.
3. Create `pinch_debug.py` and calibrate thresholds with the camera.
4. Implement active hand selection and extend the script to highlight it.
5. Add capture to the game core and show the fly, its radius and events in the script.
6. Integrate the game loop and final interface.
7. Run final live tests and tune the documented parameters.

## Out of scope for the MVP

- Controlling the fly with two hands.
- Capturing with a gesture other than the pinch.
- Reinforcement learning.

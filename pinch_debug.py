"""Pinch debug view: shows what the game evaluates for each hand.

Usage:
    uv run pinch_debug.py [--camera 0] [--model PATH]

Keys: q quit | a/z close threshold +/- | s/x open threshold +/- |
      g toggle fly and capture overlay | [ / ] fly speed -/+ | f freeze fly.
"""

import argparse
import time

import cv2

from fly_swat.game import CAPTURE_RADIUS, FLY_RADIUS, Fly, Game
from fly_swat.gestures import (
    CLOSE_RATIO,
    CONFIRM_S,
    OPEN_RATIO,
    ActiveHandSelector,
    HandState,
    HandTracker,
)
from fly_swat.vision import DEFAULT_MODEL_PATH, HandDetector, open_camera

GREEN = (0, 200, 0)
RED = (0, 0, 220)
YELLOW = (0, 220, 220)
WHITE = (255, 255, 255)
ORANGE = (0, 140, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX
THRESHOLD_STEP = 0.01
MIN_THRESHOLD_GAP = 0.02
SPEED_STEP = 0.1
MAX_SPEED_SCALE = 1.0


def put_text(frame, text, org, color=WHITE, scale=0.5):
    cv2.putText(frame, text, org, FONT, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(frame, text, org, FONT, scale, color, 1, cv2.LINE_AA)


def draw_ratio_bar(frame, hand: HandState, close_ratio, open_ratio, origin):
    """Bar from 0 to 1.2 x ref size with the close/open thresholds marked."""
    x0, y0 = origin
    width, height, max_ratio = 120, 8, 1.2

    def to_x(ratio):
        return x0 + int(min(ratio, max_ratio) / max_ratio * width)

    cv2.rectangle(frame, (x0, y0), (x0 + width, y0 + height), (60, 60, 60), -1)
    color = GREEN if hand.is_pinching else RED
    cv2.rectangle(frame, (x0, y0), (to_x(hand.ratio), y0 + height), color, -1)
    for ratio, mark in ((close_ratio, GREEN), (open_ratio, RED)):
        cv2.line(frame, (to_x(ratio), y0 - 3), (to_x(ratio), y0 + height + 3), mark, 2)
    cv2.rectangle(frame, (x0, y0), (x0 + width, y0 + height), WHITE, 1)


def draw_hand(frame, hand: HandState, active: bool, tracker: HandTracker):
    color = GREEN if hand.is_pinching else RED
    thumb = tuple(int(v) for v in hand.thumb_tip)
    tip = tuple(int(v) for v in hand.index_tip)
    mid = tuple(int(v) for v in hand.pinch_point)

    cv2.line(frame, thumb, tip, color, 2, cv2.LINE_AA)
    cv2.circle(frame, thumb, 9, color, -1, cv2.LINE_AA)
    cv2.circle(frame, tip, 9, color, -1, cv2.LINE_AA)
    put_text(frame, "T", (thumb[0] + 12, thumb[1] - 8), WHITE, 0.45)
    put_text(frame, "I", (tip[0] + 12, tip[1] - 8), WHITE, 0.45)
    cv2.drawMarker(frame, mid, YELLOW, cv2.MARKER_CROSS, 18, 2, cv2.LINE_AA)
    if active:
        cv2.circle(frame, mid, 26, ORANGE, 2, cv2.LINE_AA)

    state = "CLOSED" if hand.is_pinching else "OPEN"
    if hand.pending:
        state += " (changing...)"
    x, y = mid[0] + 20, mid[1] + 20
    put_text(frame, f"#{hand.track_id} {state}{' [ACTIVE]' if active else ''}", (x, y), color, 0.6)
    put_text(
        frame,
        f"ratio {hand.ratio:.2f}  ref {hand.ref_size:.0f}px  {hand.label} {hand.score:.2f}",
        (x, y + 18),
    )
    draw_ratio_bar(frame, hand, tracker.close_ratio, tracker.open_ratio, (x, y + 28))


def draw_fly(frame, game: Game, in_range: bool):
    center = (int(game.fly.x), int(game.fly.y))
    cv2.circle(frame, center, CAPTURE_RADIUS, GREEN if in_range else YELLOW, 1, cv2.LINE_AA)
    cv2.circle(frame, center, FLY_RADIUS, (20, 20, 20), -1, cv2.LINE_AA)
    cv2.circle(frame, center, FLY_RADIUS, (0, 0, 255), 2, cv2.LINE_AA)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--camera", type=int, default=0, help="camera index")
    parser.add_argument("--model", default=str(DEFAULT_MODEL_PATH), help="hand landmarker model")
    args = parser.parse_args()

    try:
        cap = open_camera(args.camera)
        detector = HandDetector(args.model)
    except (RuntimeError, FileNotFoundError) as error:
        raise SystemExit(str(error))

    close_ratio, open_ratio = CLOSE_RATIO, OPEN_RATIO
    speed = 1.0
    frozen = False
    tracker = HandTracker(close_ratio, open_ratio, CONFIRM_S)
    selector = ActiveHandSelector()
    game = None
    show_game = True
    captures_flash = 0.0
    last = time.perf_counter()
    last_ts = -1
    fps = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Could not receive a frame.")
                break
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            if game is None:
                game = Game(Fly(w / 2, h / 2), w, h)

            now = time.perf_counter()
            dt = max(now - last, 1e-3)
            last = now
            fps = 0.9 * fps + 0.1 / dt if fps else 1 / dt

            timestamp_ms = max(int(now * 1000), last_ts + 1)
            last_ts = timestamp_ms
            hands = tracker.update(detector.detect(frame, timestamp_ms), dt)
            active = selector.select(hands, (game.fly.x, game.fly.y), dt)

            if show_game:
                sim_dt = 0.0 if frozen else dt * speed
                if game.step(active, sim_dt):
                    captures_flash = 0.4
                draw_fly(frame, game, game.pinch_in_range(active))
            captures_flash = max(0.0, captures_flash - dt)

            for hand in hands:
                is_active = active is not None and hand.track_id == active.track_id
                draw_hand(frame, hand, is_active, tracker)

            put_text(frame, f"FPS {fps:.0f}  hands {len(hands)}", (10, 20))
            put_text(
                frame,
                f"close<= {close_ratio:.2f} (a/z)  open>= {open_ratio:.2f} (s/x)  g: game  q: quit",
                (10, 40),
            )
            if show_game:
                speed_text = "FROZEN" if frozen else f"{speed:.1f}x"
                put_text(frame, f"Captures: {game.score}  Fly speed: {speed_text} ([ ] f)", (10, 62), YELLOW, 0.6)
            if captures_flash > 0:
                put_text(frame, "CAPTURED!", (w // 2 - 80, 60), GREEN, 1.0)

            cv2.imshow("Pinch debug", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("g"):
                show_game = not show_game
            elif key == ord("f"):
                frozen = not frozen
            elif key == ord("["):
                speed = max(round(speed - SPEED_STEP, 2), 0.0)
            elif key == ord("]"):
                speed = min(round(speed + SPEED_STEP, 2), MAX_SPEED_SCALE)
            changed = True
            if key == ord("a"):
                close_ratio = min(close_ratio + THRESHOLD_STEP, open_ratio - MIN_THRESHOLD_GAP)
            elif key == ord("z"):
                close_ratio = max(close_ratio - THRESHOLD_STEP, 0.02)
            elif key == ord("s"):
                open_ratio += THRESHOLD_STEP
            elif key == ord("x"):
                open_ratio = max(open_ratio - THRESHOLD_STEP, close_ratio + MIN_THRESHOLD_GAP)
            else:
                changed = False
            if changed:
                tracker = HandTracker(close_ratio, open_ratio, CONFIRM_S)
                selector = ActiveHandSelector()
    finally:
        detector.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

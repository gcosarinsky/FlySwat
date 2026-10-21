import math
import time

import cv2

from fly_swat.game import FLY_RADIUS, Fly

# Animation parameters
FLAP_HZ = 12.0  # wing flaps per second (independent of the camera fps)


def flap_frame(t: float, n_frames: int = 2) -> int:
    """Animation frame index for a given time; also valid for real sprites."""
    return int(t * FLAP_HZ) % n_frames


def draw_fly(frame, fly: Fly, frame_index: int):
    """Placeholder sprite: circular body and wings alternating up/down."""
    center = (int(fly.x), int(fly.y))
    heading = math.degrees(math.atan2(fly.vy, fly.vx))
    wing_len = int(FLY_RADIUS * 1.2)
    wing_axes = (wing_len, wing_len // 3)
    wing_angle = 60 if frame_index == 0 else 110
    for side in (-1, 1):
        offset = (
            int(center[0] + side * FLY_RADIUS * 0.6 * math.cos(math.radians(heading + 90))),
            int(center[1] + side * FLY_RADIUS * 0.6 * math.sin(math.radians(heading + 90))),
        )
        cv2.ellipse(
            frame, offset, wing_axes, heading + side * wing_angle, 0, 360,
            (230, 230, 230), -1, cv2.LINE_AA,
        )
    cv2.circle(frame, center, FLY_RADIUS, (20, 20, 20), -1, cv2.LINE_AA)
    cv2.circle(frame, center, FLY_RADIUS, (0, 0, 255), 2, cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(0)
    fly = None
    start = last = time.perf_counter()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Could not receive a frame.")
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        if fly is None:
            fly = Fly(w / 2, h / 2)

        now = time.perf_counter()
        fly.step(now - last, w, h)
        last = now

        draw_fly(frame, fly, flap_frame(now - start))
        cv2.imshow("Fly overlay", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

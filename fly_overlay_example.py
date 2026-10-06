import math
import random
import time
from dataclasses import dataclass, field

import cv2

# Parámetros de la mosca
FLY_RADIUS = 18
MAX_SPEED = 400.0  # px/s
MAX_ACCEL = 900.0  # px/s^2
ACCEL_HOLD_S = 0.4  # tiempo que se mantiene una dirección de aceleración
DRAG = 0.5  # amortiguación por segundo
FLAP_HZ = 12.0  # aleteos por segundo (independiente del fps de la cáqmara)


@dataclass
class Fly:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    ax: float = 0.0
    ay: float = 0.0
    hold_left: float = 0.0
    rng: random.Random = field(default_factory=random.Random, repr=False)

    def _pick_accel(self):
        angle = self.rng.uniform(0, 2 * math.pi)
        self.ax = MAX_ACCEL * math.cos(angle)
        self.ay = MAX_ACCEL * math.sin(angle)
        self.hold_left = ACCEL_HOLD_S

    def step(self, dt: float, width: int, height: int):
        self.hold_left -= dt
        if self.hold_left <= 0:
            self._pick_accel()

        damping = max(0.0, 1.0 - DRAG * dt)
        self.vx = (self.vx + self.ax * dt) * damping
        self.vy = (self.vy + self.ay * dt) * damping
        speed = math.hypot(self.vx, self.vy)
        if speed > MAX_SPEED:
            self.vx *= MAX_SPEED / speed
            self.vy *= MAX_SPEED / speed

        self.x += self.vx * dt
        self.y += self.vy * dt

        r = FLY_RADIUS
        if self.x < r or self.x > width - r:
            self.x = min(max(self.x, r), width - r)
            self.vx = -self.vx
        if self.y < r or self.y > height - r:
            self.y = min(max(self.y, r), height - r)
            self.vy = -self.vy


def flap_frame(t: float, n_frames: int = 2) -> int:
    """Índice del frame de animación según el tiempo; vale para sprites reales."""
    return int(t * FLAP_HZ) % n_frames


def draw_fly(frame, fly: Fly, frame_index: int):
    """Sprite provisional: cuerpo circular y alas que alternan arriba/abajo."""
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
            print("No se pudo recibir el fotograma.")
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

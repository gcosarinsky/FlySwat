import math
import random
from dataclasses import dataclass, field

# Fly movement parameters.
FLY_RADIUS = 18
MAX_SPEED = 400.0
MAX_ACCEL = 900.0
ACCEL_HOLD_S = 0.4
DRAG = 0.5


@dataclass
class Fly:
    """Moving fly with inertia, smooth random acceleration and wall bounces.

    Physics only (no OpenCV), so it can be tested without a camera.

    Attributes:
        x, y: Position in pixels.
        vx, vy: Velocity in pixels/second.
        ax, ay: Current acceleration in pixels/second^2.
        hold_left: Seconds left before a new random acceleration is chosen.
        rng: Per-instance random generator (pass a seeded one for
            reproducible trajectories).
    """

    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    ax: float = 0.0
    ay: float = 0.0
    hold_left: float = 0.0
    rng: random.Random = field(default_factory=random.Random, repr=False)

    def _pick_accel(self):
        """Choose a random acceleration direction and hold it for ACCEL_HOLD_S."""
        angle = self.rng.uniform(0, 2 * math.pi)
        self.ax = MAX_ACCEL * math.cos(angle)
        self.ay = MAX_ACCEL * math.sin(angle)
        self.hold_left = ACCEL_HOLD_S

    def step(self, dt: float, width: int, height: int):
        """Advance the simulation by dt seconds inside a width x height area.

        Applies acceleration, drag and the MAX_SPEED limit, then moves the fly
        and reflects its velocity when it touches a border.
        """
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

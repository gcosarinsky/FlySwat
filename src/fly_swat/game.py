import math
import random
from dataclasses import dataclass, field

from fly_swat.gestures import HandState, distance

# Fly movement parameters.
FLY_RADIUS = 18
# A pinch captures the fly when its point is within this distance of the fly.
CAPTURE_RADIUS = FLY_RADIUS + 12
# After a capture the fly reappears at least this far from the hand.
RESPAWN_MIN_DISTANCE = 4 * CAPTURE_RADIUS
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


@dataclass(frozen=True)
class CaptureEvent:
    """The fly was captured at (x, y)."""

    x: float
    y: float


@dataclass
class Game:
    """Fly, capture rule and score. No camera or rendering dependencies.

    A capture needs the pinch to close (open -> closed) while within
    CAPTURE_RADIUS of the fly. A pinch that was already closed when the fly
    came close does not count; it must be released and closed again.
    """

    fly: Fly
    width: int
    height: int
    score: int = 0
    _prev_track_id: int | None = field(default=None, repr=False)
    _prev_pinching: bool = field(default=False, repr=False)

    def pinch_in_range(self, hand: HandState | None) -> bool:
        """True if the hand's pinch point is within the capture radius."""
        return hand is not None and (
            distance(hand.pinch_point, (self.fly.x, self.fly.y)) <= CAPTURE_RADIUS
        )

    def step(self, hand: HandState | None, dt: float) -> list[CaptureEvent]:
        """Advance the fly and apply the capture rule for the active hand."""
        self.fly.step(dt, self.width, self.height)

        if hand is None:
            self._prev_track_id = None
            self._prev_pinching = False
            return []

        # A newly active hand has no previous state, so it cannot "close".
        was_pinching = (
            self._prev_pinching if hand.track_id == self._prev_track_id else hand.is_pinching
        )
        self._prev_track_id = hand.track_id
        self._prev_pinching = hand.is_pinching

        if was_pinching or not hand.is_pinching or not self.pinch_in_range(hand):
            return []

        self.score += 1
        event = CaptureEvent(self.fly.x, self.fly.y)
        self._respawn(hand.pinch_point)
        return [event]

    def _respawn(self, away_from: tuple[float, float]):
        """Move the fly to a random spot away from the given point."""
        r = FLY_RADIUS
        for _ in range(20):
            x = self.fly.rng.uniform(r, self.width - r)
            y = self.fly.rng.uniform(r, self.height - r)
            if distance((x, y), away_from) >= RESPAWN_MIN_DISTANCE:
                break
        self.fly.x, self.fly.y = x, y
        self.fly.vx = self.fly.vy = 0.0

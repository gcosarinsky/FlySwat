"""Pinch detection and active hand selection.

Pure logic (no OpenCV or MediaPipe), so it can be tested without a camera.
All positions are in pixels of the mirrored image shown to the player.
"""

import math
from dataclasses import dataclass

Vec2 = tuple[float, float]

# Pinch thresholds, as a ratio of (thumb-index tip distance) / (hand reference size).
CLOSE_RATIO = 0.25  # at or below this the pinch closes
OPEN_RATIO = 0.45  # at or above this the pinch opens (wider than CLOSE_RATIO)
CONFIRM_S = 0.05  # a state change must persist this long to be accepted

# A tracked hand may move at most this many reference sizes between frames.
MAX_JUMP_REFS = 3.0

# Seconds a different hand must be preferred before the active hand switches.
SWITCH_DELAY_S = 0.15


def distance(a: Vec2, b: Vec2) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


@dataclass(frozen=True)
class RawHand:
    """Per-frame measurements of one hand, as extracted from the landmarks.

    Attributes:
        thumb_tip, index_tip: Fingertip positions in pixels.
        ref_size: Hand size in pixels (wrist to middle finger base), used to
            make thresholds independent of the distance to the camera.
        label: "Left" or "Right". Informational only, not a stable identity.
        score: Handedness confidence in [0, 1].
    """

    thumb_tip: Vec2
    index_tip: Vec2
    ref_size: float
    label: str = ""
    score: float = 1.0

    @property
    def pinch_point(self) -> Vec2:
        return (
            (self.thumb_tip[0] + self.index_tip[0]) / 2,
            (self.thumb_tip[1] + self.index_tip[1]) / 2,
        )

    @property
    def ratio(self) -> float:
        """Thumb-index distance relative to the hand size."""
        return distance(self.thumb_tip, self.index_tip) / max(self.ref_size, 1e-6)


@dataclass(frozen=True)
class HandState:
    """A tracked hand with a stable id and a debounced pinch state.

    Attributes:
        track_id: Identity kept across frames by spatial continuity.
        is_pinching: Debounced pinch state (closed = True).
        pending: True while a state change is waiting to be confirmed.
    """

    track_id: int
    thumb_tip: Vec2
    index_tip: Vec2
    pinch_point: Vec2
    ref_size: float
    ratio: float
    is_pinching: bool
    pending: bool = False
    label: str = ""
    score: float = 1.0


class PinchDetector:
    """Debounced pinch state with hysteresis and temporal stability."""

    def __init__(
        self,
        close_ratio: float = CLOSE_RATIO,
        open_ratio: float = OPEN_RATIO,
        confirm_s: float = CONFIRM_S,
    ):
        if close_ratio >= open_ratio:
            raise ValueError("close_ratio must be smaller than open_ratio")
        self.close_ratio = close_ratio
        self.open_ratio = open_ratio
        self.confirm_s = confirm_s
        self.is_pinching = False
        self.pending = False
        self._pending_s = 0.0

    def update(self, ratio: float, dt: float) -> bool:
        """Feed one measurement and return the (debounced) pinch state."""
        target = self.is_pinching
        if not self.is_pinching and ratio <= self.close_ratio:
            target = True
        elif self.is_pinching and ratio >= self.open_ratio:
            target = False

        if target == self.is_pinching:
            self.pending = False
            self._pending_s = 0.0
        else:
            self.pending = True
            self._pending_s += dt
            if self._pending_s >= self.confirm_s:
                self.is_pinching = target
                self.pending = False
                self._pending_s = 0.0
        return self.is_pinching


class HandTracker:
    """Gives hands a stable id across frames and a debounced pinch state."""

    def __init__(
        self,
        close_ratio: float = CLOSE_RATIO,
        open_ratio: float = OPEN_RATIO,
        confirm_s: float = CONFIRM_S,
    ):
        self.close_ratio = close_ratio
        self.open_ratio = open_ratio
        self.confirm_s = confirm_s
        self._next_id = 0
        # track_id -> (last pinch point, detector)
        self._tracks: dict[int, tuple[Vec2, PinchDetector]] = {}

    def update(self, raw_hands: list[RawHand], dt: float) -> list[HandState]:
        """Match raw hands to existing tracks and update their pinch states."""
        pairs = sorted(
            (distance(hand.pinch_point, point), track_id, i)
            for i, hand in enumerate(raw_hands)
            for track_id, (point, _) in self._tracks.items()
        )
        assigned: dict[int, int] = {}  # raw index -> track_id
        used_tracks: set[int] = set()
        for dist, track_id, i in pairs:
            if i in assigned or track_id in used_tracks:
                continue
            if dist > MAX_JUMP_REFS * raw_hands[i].ref_size:
                continue
            assigned[i] = track_id
            used_tracks.add(track_id)

        tracks = {}
        states = []
        for i, hand in enumerate(raw_hands):
            track_id = assigned.get(i)
            if track_id is None:
                track_id = self._next_id
                self._next_id += 1
                detector = PinchDetector(self.close_ratio, self.open_ratio, self.confirm_s)
            else:
                detector = self._tracks[track_id][1]
            detector.update(hand.ratio, dt)
            tracks[track_id] = (hand.pinch_point, detector)
            states.append(
                HandState(
                    track_id=track_id,
                    thumb_tip=hand.thumb_tip,
                    index_tip=hand.index_tip,
                    pinch_point=hand.pinch_point,
                    ref_size=hand.ref_size,
                    ratio=hand.ratio,
                    is_pinching=detector.is_pinching,
                    pending=detector.pending,
                    label=hand.label,
                    score=hand.score,
                )
            )
        self._tracks = tracks
        return states


def _closest(hands: list[HandState], point: Vec2) -> HandState:
    return min(hands, key=lambda hand: distance(hand.pinch_point, point))


class ActiveHandSelector:
    """Chooses the single hand that controls the game.

    Preference order: the only pinching hand; else the pinching hand closest
    to the fly; else the previous active hand while it is detected; else the
    hand closest to the fly. Switching to a different hand only happens after
    it has been preferred for SWITCH_DELAY_S, unless the active hand is lost.
    """

    def __init__(self, switch_delay_s: float = SWITCH_DELAY_S):
        self.switch_delay_s = switch_delay_s
        self.active_id: int | None = None
        self._candidate_id: int | None = None
        self._candidate_s = 0.0

    def _preferred(self, hands: list[HandState], fly_pos: Vec2) -> HandState:
        pinching = [hand for hand in hands if hand.is_pinching]
        if len(pinching) == 1:
            return pinching[0]
        if pinching:
            return _closest(pinching, fly_pos)
        for hand in hands:
            if hand.track_id == self.active_id:
                return hand
        return _closest(hands, fly_pos)

    def select(
        self, hands: list[HandState], fly_pos: Vec2, dt: float
    ) -> HandState | None:
        """Return the active hand for this frame, or None if no hand is seen."""
        if not hands:
            self.active_id = None
            self._candidate_id = None
            self._candidate_s = 0.0
            return None

        preferred = self._preferred(hands, fly_pos)
        active = next((h for h in hands if h.track_id == self.active_id), None)

        if active is None:
            self.active_id = preferred.track_id
            self._candidate_id = None
            self._candidate_s = 0.0
            return preferred

        if preferred.track_id == active.track_id:
            self._candidate_id = None
            self._candidate_s = 0.0
            return active

        if self._candidate_id != preferred.track_id:
            self._candidate_id = preferred.track_id
            self._candidate_s = 0.0
        self._candidate_s += dt
        if self._candidate_s >= self.switch_delay_s:
            self.active_id = preferred.track_id
            self._candidate_id = None
            self._candidate_s = 0.0
            return preferred
        return active

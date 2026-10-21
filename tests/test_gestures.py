import unittest

from fly_swat.gestures import (
    ActiveHandSelector,
    HandState,
    HandTracker,
    PinchDetector,
    RawHand,
)


def raw_hand(x=100.0, y=100.0, gap=100.0, ref=100.0):
    """Hand whose thumb and index tips are `gap` px apart, centered at (x, y)."""
    return RawHand((x - gap / 2, y), (x + gap / 2, y), ref)


def hand_state(track_id, point, pinching):
    return HandState(
        track_id=track_id,
        thumb_tip=point,
        index_tip=point,
        pinch_point=point,
        ref_size=100.0,
        ratio=0.1 if pinching else 1.0,
        is_pinching=pinching,
    )


class PinchDetectorTests(unittest.TestCase):
    def make(self):
        return PinchDetector(close_ratio=0.25, open_ratio=0.45, confirm_s=0.05)

    def test_closes_after_confirmation_time(self):
        detector = self.make()

        self.assertFalse(detector.update(0.1, 0.03))
        self.assertTrue(detector.pending)
        self.assertTrue(detector.update(0.1, 0.03))
        self.assertFalse(detector.pending)

    def test_single_noisy_frame_is_ignored(self):
        detector = self.make()

        detector.update(0.1, 0.03)
        detector.update(0.8, 0.03)
        self.assertFalse(detector.update(0.8, 0.03))

    def test_hysteresis_keeps_state_between_thresholds(self):
        detector = self.make()
        for _ in range(3):
            detector.update(0.1, 0.03)
        self.assertTrue(detector.is_pinching)

        for _ in range(10):
            detector.update(0.35, 0.03)

        self.assertTrue(detector.is_pinching)

    def test_opens_above_open_threshold(self):
        detector = self.make()
        for _ in range(3):
            detector.update(0.1, 0.03)

        for _ in range(3):
            detector.update(0.5, 0.03)

        self.assertFalse(detector.is_pinching)

    def test_invalid_thresholds_are_rejected(self):
        with self.assertRaises(ValueError):
            PinchDetector(close_ratio=0.5, open_ratio=0.4)


class RawHandTests(unittest.TestCase):
    def test_pinch_point_and_ratio(self):
        hand = RawHand((90.0, 100.0), (110.0, 100.0), ref_size=100.0)

        self.assertEqual(hand.pinch_point, (100.0, 100.0))
        self.assertAlmostEqual(hand.ratio, 0.2)

    def test_ratio_is_independent_of_hand_scale(self):
        near = raw_hand(gap=40, ref=200)
        far = raw_hand(gap=10, ref=50)

        self.assertAlmostEqual(near.ratio, far.ratio)


class HandTrackerTests(unittest.TestCase):
    def test_keeps_ids_across_frames_even_if_order_changes(self):
        tracker = HandTracker()
        first = tracker.update([raw_hand(100), raw_hand(500)], 0.03)

        second = tracker.update([raw_hand(505), raw_hand(102)], 0.03)

        self.assertEqual(second[0].track_id, first[1].track_id)
        self.assertEqual(second[1].track_id, first[0].track_id)

    def test_pinch_states_are_independent_per_hand(self):
        tracker = HandTracker()
        for _ in range(3):
            states = tracker.update([raw_hand(100, gap=10), raw_hand(500, gap=100)], 0.03)

        self.assertEqual([s.is_pinching for s in states], [True, False])

    def test_far_jump_creates_a_new_track(self):
        tracker = HandTracker()
        first = tracker.update([raw_hand(100)], 0.03)

        second = tracker.update([raw_hand(1000)], 0.03)

        self.assertNotEqual(first[0].track_id, second[0].track_id)


class ActiveHandSelectorTests(unittest.TestCase):
    fly = (0.0, 0.0)

    def test_no_hands_returns_none(self):
        self.assertIsNone(ActiveHandSelector().select([], self.fly, 0.03))

    def test_single_pinching_hand_wins(self):
        selector = ActiveHandSelector(switch_delay_s=0)
        hands = [hand_state(1, (10, 0), False), hand_state(2, (500, 0), True)]

        self.assertEqual(selector.select(hands, self.fly, 0.03).track_id, 2)

    def test_both_pinching_chooses_closest_to_fly(self):
        selector = ActiveHandSelector(switch_delay_s=0)
        hands = [hand_state(1, (300, 0), True), hand_state(2, (50, 0), True)]

        self.assertEqual(selector.select(hands, self.fly, 0.03).track_id, 2)

    def test_none_pinching_without_previous_chooses_closest(self):
        selector = ActiveHandSelector()
        hands = [hand_state(1, (300, 0), False), hand_state(2, (50, 0), False)]

        self.assertEqual(selector.select(hands, self.fly, 0.03).track_id, 2)

    def test_none_pinching_keeps_previous_active_hand(self):
        selector = ActiveHandSelector()
        selector.select([hand_state(1, (300, 0), False), hand_state(2, (50, 0), False)], self.fly, 0.03)

        hands = [hand_state(1, (10, 0), False), hand_state(2, (300, 0), False)]
        selected = selector.select(hands, self.fly, 0.03)

        self.assertEqual(selected.track_id, 2)

    def test_switch_requires_delay(self):
        selector = ActiveHandSelector(switch_delay_s=0.1)
        selector.select([hand_state(1, (50, 0), False), hand_state(2, (300, 0), False)], self.fly, 0.03)
        hands = [hand_state(1, (50, 0), False), hand_state(2, (300, 0), True)]

        first = selector.select(hands, self.fly, 0.06)
        second = selector.select(hands, self.fly, 0.06)

        self.assertEqual(first.track_id, 1)
        self.assertEqual(second.track_id, 2)

    def test_switches_immediately_when_active_hand_is_lost(self):
        selector = ActiveHandSelector(switch_delay_s=10)
        selector.select([hand_state(1, (50, 0), False)], self.fly, 0.03)

        selected = selector.select([hand_state(2, (300, 0), False)], self.fly, 0.03)

        self.assertEqual(selected.track_id, 2)


if __name__ == "__main__":
    unittest.main()

import random
import unittest

from fly_swat.game import CAPTURE_RADIUS, MAX_SPEED, Fly, Game
from fly_swat.gestures import HandState


def hand_at(x, y, pinching):
    return HandState(
        track_id=0,
        thumb_tip=(x, y),
        index_tip=(x, y),
        pinch_point=(x, y),
        ref_size=100.0,
        ratio=0.1 if pinching else 1.0,
        is_pinching=pinching,
    )


def make_game():
    fly = Fly(300, 200, rng=random.Random(1), hold_left=100)
    return Game(fly, 640, 480)


class CaptureTests(unittest.TestCase):
    def test_open_pinch_does_not_capture(self):
        game = make_game()

        events = game.step(hand_at(300, 200, False), 0.001)

        self.assertEqual((events, game.score), ([], 0))

    def test_pinch_outside_radius_does_not_capture(self):
        game = make_game()

        events = game.step(hand_at(300 + CAPTURE_RADIUS + 20, 200, True), 0.001)

        self.assertEqual((events, game.score), ([], 0))

    def test_no_hand_does_not_capture(self):
        game = make_game()

        self.assertEqual(game.step(None, 0.001), [])

    def test_closed_pinch_in_range_captures_once_while_held(self):
        game = make_game()

        first = game.step(hand_at(300, 200, True), 0.001)
        game.fly.x, game.fly.y = 300, 200
        second = game.step(hand_at(300, 200, True), 0.001)

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(game.score, 1)

    def test_releasing_pinch_allows_another_capture(self):
        game = make_game()
        game.step(hand_at(300, 200, True), 0.001)
        game.step(hand_at(300, 200, False), 0.001)
        game.fly.x, game.fly.y = 300, 200

        events = game.step(hand_at(300, 200, True), 0.001)

        self.assertEqual(len(events), 1)
        self.assertEqual(game.score, 2)

    def test_fly_respawns_away_from_hand_after_capture(self):
        game = make_game()

        game.step(hand_at(300, 200, True), 0.001)

        self.assertFalse(game.pinch_in_range(hand_at(300, 200, True)))


class FlyPhysicsTests(unittest.TestCase):
    def test_step_limits_speed(self):
        fly = Fly(100, 100, vx=1000, hold_left=1)

        fly.step(0.01, 640, 480)

        self.assertAlmostEqual((fly.vx**2 + fly.vy**2) ** 0.5, MAX_SPEED)

    def test_step_reflects_velocity_at_both_borders(self):
        fly = Fly(80, 80, vx=20, vy=20, hold_left=2)

        fly.step(1, 100, 100)

        self.assertEqual((fly.x, fly.y), (82, 82))
        self.assertEqual((fly.vx, fly.vy), (-10, -10))

    def test_seeded_random_generators_produce_matching_trajectories(self):
        flies = [
            Fly(100, 100, rng=random.Random(42)),
            Fly(100, 100, rng=random.Random(42)),
        ]

        for _ in range(5):
            for fly in flies:
                fly.step(0.1, 640, 480)

        self.assertEqual(
            (flies[0].x, flies[0].y, flies[0].vx, flies[0].vy, flies[0].ax, flies[0].ay),
            (flies[1].x, flies[1].y, flies[1].vx, flies[1].vy, flies[1].ax, flies[1].ay),
        )


if __name__ == "__main__":
    unittest.main()

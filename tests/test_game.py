import random
import unittest

from fly_swat.game import MAX_SPEED, Fly


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

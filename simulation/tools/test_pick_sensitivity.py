"""python3 -m unittest discover -s simulation/tools -p 'test_*.py'"""
import json
import unittest
from pathlib import Path

import pick_sensitivity as ps


class SolveTest(unittest.TestCase):
    def test_finds_crossing(self):
        self.assertAlmostEqual(ps.solve(lambda p: 1 / p, 2.0), 0.5, places=6)

    def test_unreachable_returns_none_not_upper_bound(self):
        # Before 2026-11-01 this returned 0.95 and read as "break-even at 95%".
        self.assertIsNone(ps.solve(lambda p: 10.0, 1.0))

    def test_already_cheap_at_lower_bound(self):
        self.assertEqual(ps.solve(lambda p: 0.1, 1.0), 0.05)


class HarvesterTest(unittest.TestCase):
    def test_reproduces_the_review_hand_calculation(self):
        # AI harvester review, 2026-11-01: about 48% at $36k and 57% at $48k.
        self.assertAlmostEqual(ps.harvester_break_even(36_400), 0.48, delta=0.02)
        self.assertAlmostEqual(ps.harvester_break_even(48_342), 0.57, delta=0.02)

    def test_us_sourced_robot_cannot_break_even_in_one_season(self):
        self.assertIsNone(ps.harvester_break_even(125_395))
        self.assertGreater(ps.harvester(125_395, 1.0)["robot_usd_per_kg"], ps.HARVESTER["crew_usd_h"] / ps.HARVESTER["crew_kg_h"])

    def test_fast_crews_kill_break_even(self):
        self.assertIsNone(ps.harvester_break_even(51_942, crew_kg_h=150))

    def test_pilot_discount_raises_break_even(self):
        self.assertGreater(ps.harvester_break_even(48_342, price_discount=0.15), ps.harvester_break_even(48_342))

    def test_crew_equivalents_ceiling(self):
        # 5.3 s/fruit at 0.2 kg is about 136 kg/h at 100%, about 1.6 crew members at 85 kg/h.
        self.assertAlmostEqual(ps.harvester(48_342, 1.0)["crew_equivalents"], 1.6, delta=0.05)

    def test_max_robot_price_is_consistent_with_break_even(self):
        usd = ps.max_robot_usd(0.55)
        self.assertAlmostEqual(ps.harvester_break_even(usd), 0.55, delta=0.005)

    def test_bad_inputs_raise(self):
        for kw in (dict(cycle_s=0), dict(hours_per_year=0), dict(crew_kg_h=0)):
            with self.assertRaises(ValueError):
                ps.harvester(48_342, 0.5, **kw)


class SeasonSimTest(unittest.TestCase):
    def test_sim_assumption_reproduces_reported_opex(self):
        results = Path(__file__).resolve().parents[1] / "results"
        rep = json.loads((results / "pick_sensitivity.json").read_text())
        sim = next(p for p in rep["points"] if p["pick_success"] == ps.SIM_P)
        self.assertAlmostEqual(sim["agrobo_usd_per_kg"], 0.185, delta=0.005)


if __name__ == "__main__":
    unittest.main()

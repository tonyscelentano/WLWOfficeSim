from __future__ import annotations

import unittest

from src.systems.career import (
    SUBSCRIBED_EVENTS,
    apply_promotion,
    check_promotion_eligibility,
    handle_bus_event,
)


class CareerTests(unittest.TestCase):
    def test_known_bus_events_are_declared(self) -> None:
        self.assertIn("task_failed", SUBSCRIBED_EVENTS)
        self.assertIn("presence_trait_updated", SUBSCRIBED_EVENTS)

    def test_promotion_requires_manager(self) -> None:
        result = check_promotion_eligibility({"reputation": 80, "xp": 200})
        self.assertFalse(result["eligible"])
        self.assertIn("missing_manager", result["blockers"])

    def test_promotion_eligibility_uses_snapshot_relationships(self) -> None:
        snapshot = {
            "reports_to": "alex_lead",
            "reputation": 70,
            "xp": 150,
            "relationships": {
                "alex_lead": {"trust": 80, "rivalry": 0},
            },
        }
        result = check_promotion_eligibility(snapshot)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["metrics"]["manager_trust"], 80)

    def test_presence_trait_effects_match_engine_trait_names(self) -> None:
        result = handle_bus_event(
            "presence_trait_updated",
            {"trait": "overachiever"},
            {"reports_to": "alex_lead"},
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertGreater(result["rep_delta"], 0)

    def test_deadline_failure_without_outcome_still_penalizes(self) -> None:
        result = handle_bus_event(
            "task_failed",
            {"task_id": "client_demo_prep"},
            {"reports_to": "alex_lead"},
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertLess(result["rep_delta"], 0)
        self.assertGreater(result["stress_delta"], 0)

    def test_apply_promotion_returns_standard_result_shape(self) -> None:
        result = apply_promotion({"title": "Junior Backend Dev"})
        self.assertEqual(result["outcome"], "success")
        self.assertIn("money_delta", result)
        self.assertIn("npc_deltas", result)


if __name__ == "__main__":
    unittest.main()

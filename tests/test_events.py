from __future__ import annotations

import random
import unittest

from src.systems.events import eligible_events, normalize_event_template, pick_event, resolve_event


class EventScaffoldingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = {
            "day": 3,
            "stress": 45,
            "department": "technical.middle.backend",
            "presence_trait": "overachiever",
        }
        self.events = [
            {
                "id": "all_hands",
                "title": "Surprise All Hands",
                "type": "meeting",
                "weight": 2,
                "min_day": 1,
                "max_day": 10,
                "effects": {"energy_delta": -15, "stress_delta": 5},
            },
            {
                "id": "layoff_rumors",
                "title": "Layoff Rumors",
                "type": "politics",
                "min_stress": 50,
                "effects": {"stress_delta": 20},
            },
        ]

    def test_normalize_event_template_sets_defaults(self) -> None:
        event = normalize_event_template({"id": "test_event"})
        self.assertEqual(event["title"], "Untitled Event")
        self.assertEqual(event["effects"]["rep_delta"], 0)

    def test_eligible_events_filters_by_snapshot_constraints(self) -> None:
        results = eligible_events(self.events, self.snapshot)
        ids = {event["id"] for event in results}
        self.assertIn("all_hands", ids)
        self.assertNotIn("layoff_rumors", ids)

    def test_pick_event_returns_weighted_candidate(self) -> None:
        event = pick_event(self.events, self.snapshot, rng=random.Random(7))
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["id"], "all_hands")

    def test_resolve_event_returns_engine_result_shape(self) -> None:
        result = resolve_event(self.events[0])
        self.assertIn("energy_delta", result)
        self.assertIn("npc_deltas", result)
        self.assertEqual(result["stress_delta"], 5)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from src.systems.events import eligible_events, pick_event, resolve_event


EVENT_FILE = Path(__file__).resolve().parents[1] / "src" / "data" / "events.toml"


class EventContentTests(unittest.TestCase):
    def setUp(self) -> None:
        with EVENT_FILE.open("rb") as f:
            self.events = tomllib.load(f).get("events", [])

    def test_sales_and_product_event_pack_exists(self) -> None:
        self.assertGreaterEqual(len(self.events), 8)
        departments = {event["department"] for event in self.events}
        self.assertIn("fulfillment.middle.product", departments)
        self.assertIn("fulfillment.right.sales", departments)

    def test_event_pack_has_pitch_meeting_buzzword_events(self) -> None:
        tagged = [
            event for event in self.events
            if "pitch" in event.get("tags", []) and "meeting" in event.get("tags", [])
        ]
        self.assertGreaterEqual(len(tagged), 3)

    def test_product_snapshot_finds_product_events(self) -> None:
        snapshot = {
            "day": 4,
            "stress": 30,
            "department": "fulfillment.middle.product",
            "presence_trait": "solid_nine_to_five",
        }
        events = eligible_events(self.events, snapshot)
        ids = {event["id"] for event in events}
        self.assertIn("product_vision_alignment_jam", ids)
        self.assertIn("roadmap_reprioritization_theater", ids)

    def test_sales_snapshot_can_pick_and_resolve_sales_event(self) -> None:
        snapshot = {
            "day": 4,
            "stress": 35,
            "department": "fulfillment.right.sales",
            "presence_trait": "overachiever",
        }
        picked = pick_event(self.events, snapshot)
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertEqual(picked["department"], "fulfillment.right.sales")
        result = resolve_event(picked)
        self.assertTrue({"pitch", "client"} & set(picked["tags"]))
        self.assertIn("stress_delta", result)
        self.assertIn("rep_delta", result)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from src.systems.relationship_perks import (
    npc_access_perks,
    relationship_tier,
    summarize_relationship_perks,
)


NPCS = [
    {
        "id": "maya_csm",
        "social_currency": "client_cover",
        "access_tags": ["client", "executive", "revenue"],
        "influence_weight": 8,
        "base_trust": 50,
        "base_rivalry": 0,
    },
    {
        "id": "nina_sales",
        "social_currency": "pipeline_heat",
        "access_tags": ["sales", "client", "gossip"],
        "influence_weight": 7,
        "base_trust": 15,
        "base_rivalry": 10,
    },
    {
        "id": "jason_it",
        "social_currency": "it_air_cover",
        "access_tags": ["engineering", "infrastructure"],
        "influence_weight": 6,
        "base_trust": 55,
        "base_rivalry": 5,
    },
]


class RelationshipPerksTests(unittest.TestCase):
    def test_relationship_tier_prioritizes_high_rivalry(self) -> None:
        self.assertEqual(relationship_tier(90, 70), "rival")
        self.assertEqual(relationship_tier(82, 10), "sponsor")

    def test_npc_access_perks_unlocks_tags_for_allies(self) -> None:
        snapshot = {"relationships": {"maya_csm": {"trust": 65, "rivalry": 5}}}
        perks = npc_access_perks(NPCS[0], snapshot)
        self.assertEqual(perks["tier"], "ally")
        self.assertIn("client", perks["unlocked_access"])

    def test_summary_collects_sponsors_and_rivalries(self) -> None:
        snapshot = {
            "relationships": {
                "maya_csm": {"trust": 85, "rivalry": 5},
                "nina_sales": {"trust": 40, "rivalry": 80},
            }
        }
        summary = summarize_relationship_perks(NPCS, snapshot)
        self.assertIn("maya_csm", summary["sponsors"])
        self.assertIn("nina_sales", summary["rivalries"])
        self.assertIn("client", summary["unlocked_access"])

    def test_jason_relationship_exposes_mechanical_benefit_stubs(self) -> None:
        snapshot = {"relationships": {"jason_it": {"trust": 70, "rivalry": 5}}}

        perks = npc_access_perks(NPCS[2], snapshot)

        self.assertEqual(perks["tier"], "ally")
        self.assertIn("engineering_task_assist_stub", perks["mechanical_benefits"])


if __name__ == "__main__":
    unittest.main()

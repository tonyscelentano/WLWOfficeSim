from __future__ import annotations

import unittest

from src.core.loader import load_factions
from src.core.loader import load_npcs
from src.systems.social_economy import (
    CLUSTER_ADJACENCY,
    rank_social_targets,
    resolve_social_action,
    social_action_plan,
    social_opportunity_score,
    summarize_cluster_map,
)


NPCS = [
    {
        "id": "alex_lead",
        "archetype": "chaotic_genius",
        "pillar": "technical",
        "cluster": "backend",
        "influence_weight": 7,
        "ambition": 3,
        "base_trust": 20,
        "base_rivalry": 0,
        "social_currency": "technical_credibility",
        "access_tags": ["engineering"],
    },
    {
        "id": "maya_csm",
        "archetype": "political",
        "pillar": "fulfillment",
        "cluster": "csm",
        "influence_weight": 8,
        "ambition": 7,
        "base_trust": 50,
        "base_rivalry": 0,
        "social_currency": "client_cover",
        "access_tags": ["client"],
    },
]


class SocialEconomyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.player_snapshot = {
            "department": "technical.middle.backend",
            "presence_trait": "overachiever",
            "relationships": {
                "alex_lead": {"trust": 45, "rivalry": 5},
                "maya_csm": {"trust": 55, "rivalry": 0},
            },
        }
        self.factions = load_factions()

    def test_social_score_uses_org_topology_metadata(self) -> None:
        score = social_opportunity_score(NPCS[1], self.player_snapshot, self.factions)
        self.assertIn("mapped_to_org_topology", score["reasons"])
        self.assertEqual(score["social_currency"], "client_cover")

    def test_same_cluster_bonus_beats_cross_org_when_influence_is_close(self) -> None:
        score = social_opportunity_score(NPCS[0], self.player_snapshot, self.factions)
        self.assertEqual(score["cluster_distance"], 0)
        self.assertIn("same_cluster_access", score["reasons"])

    def test_ranked_targets_sorted_by_score(self) -> None:
        ranked = rank_social_targets(NPCS, self.player_snapshot, self.factions)
        self.assertEqual(len(ranked), 2)
        self.assertGreaterEqual(ranked[0]["score"], ranked[1]["score"])

    def test_cluster_map_flattens_faction_tree(self) -> None:
        cluster_map = summarize_cluster_map(self.factions)
        self.assertIn("backend", cluster_map)
        self.assertEqual(cluster_map["backend"]["pillar"], "technical")
        self.assertIn("architecture", cluster_map["backend"]["adjacent_clusters"])
        self.assertIn("architecture", CLUSTER_ADJACENCY["backend"])

    def test_social_action_plan_marks_cross_org_favor_as_risky(self) -> None:
        plan = social_action_plan("ask_for_favor", NPCS[1], self.player_snapshot, self.factions)
        self.assertFalse(plan["recommended"])
        self.assertGreater(plan["estimated_risk"], 0)

    def test_resolve_social_action_returns_standard_result_shape(self) -> None:
        result = resolve_social_action("seek_mentorship", NPCS[0], self.player_snapshot, self.factions)
        self.assertIn("xp_delta", result)
        self.assertIn("npc_deltas", result)
        self.assertIn("alex_lead", result["npc_deltas"])

    def test_npc_loader_accepts_topology_enriched_records(self) -> None:
        npcs = load_npcs()
        self.assertGreaterEqual(len(npcs), 2)
        first = npcs[0]
        self.assertIn("pillar", first)
        self.assertIn("social_currency", first)


if __name__ == "__main__":
    unittest.main()

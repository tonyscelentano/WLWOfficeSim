from __future__ import annotations

import unittest

from src.systems.social_actions import execute_social_action, is_social_action, list_social_actions, plan_social_action


class SocialActionsRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.npc = {
            "id": "alex_lead",
            "name": "Alex",
            "archetype": "chaotic_genius",
            "pillar": "technical",
            "cluster": "backend",
            "influence_weight": 7,
            "ambition": 3,
            "base_trust": 20,
            "base_rivalry": 0,
            "social_currency": "technical_credibility",
            "access_tags": ["engineering"],
        }
        self.player_snapshot = {
            "department": "technical.middle.backend",
            "presence_trait": "overachiever",
            "relationships": {
                "alex_lead": {"trust": 45, "rivalry": 0},
            },
        }

    def test_registry_lists_known_actions(self) -> None:
        actions = list_social_actions()
        self.assertIn("seek_mentorship", actions)
        self.assertTrue(is_social_action("small_talk"))
        self.assertFalse(is_social_action("start_coup"))

    def test_plan_social_action_returns_planner_payload(self) -> None:
        plan = plan_social_action("seek_mentorship", self.npc, self.player_snapshot)
        self.assertEqual(plan["action"], "seek_mentorship")
        self.assertIn("target_score", plan)

    def test_execute_social_action_returns_result_shape(self) -> None:
        result = execute_social_action("relationship_maintenance", self.npc, self.player_snapshot)
        self.assertEqual(result["outcome"], "success")
        self.assertIn("npc_deltas", result)


if __name__ == "__main__":
    unittest.main()

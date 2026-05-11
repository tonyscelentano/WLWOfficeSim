from __future__ import annotations

import unittest
from unittest.mock import patch

from src.core.engine import Engine
from quests.literal_gremlins import QUEST_ID


def _engine_with_jason() -> Engine:
    engine = Engine()
    engine._initialized = True
    engine.data = {
        "npcs": [
            {
                "id": "jason_it",
                "name": "Jason",
                "role": "IT Support / Tech Purist",
                "pfp": "Jason-Basement_IT.png",
                "archetype": "operator",
                "base_trust": 55,
                "base_rivalry": 5,
                "watercooler_scene": "IT-Basement_Bored-Technician.jpeg",
                "watercooler_seed": "Jason stares at an MS-DOS prompt.",
                "watercooler_pool": False,
            }
        ],
        "interactions": {"operator": {"id": "operator", "templates": ["Jason evaluates your idea."]}},
    }
    return engine


class EngineGremlinQuestTests(unittest.TestCase):
    def test_visit_it_auto_starts_gremlin_quest_without_input(self) -> None:
        engine = _engine_with_jason()
        result = engine._resolve_visit_it()

        self.assertEqual(result.get("npc_id"), "jason_it")
        self.assertIn(QUEST_ID, engine.state.player.quests)
        self.assertEqual(engine.state.player.quests[QUEST_ID]["stage"], "stabilize_racks")
        self.assertEqual(engine.state.player.quests[QUEST_ID]["status"], "active")
        self.assertEqual(result.get("scene"), "SCENE_GREMLINS")

    def test_visit_it_action_preserves_quest_scene(self) -> None:
        engine = _engine_with_jason()
        result = engine.handle_action("visit_it")

        self.assertEqual(result.get("npc_id"), "jason_it")
        self.assertEqual(result.get("scene"), "SCENE_GREMLINS")

    @patch("quests.literal_gremlins.call_llm_json", return_value=None)
    def test_active_quest_uses_fallback_and_advances_stage(self, _mock_llm: object) -> None:
        engine = _engine_with_jason()
        engine.state.player.quests["gremlins"] = {"stage": 1, "score": 0}

        result = engine._resolve_socialize(
            npc_id="jason_it",
            player_input="I will shield the fiber network and reroute damaged cables.",
        )

        self.assertEqual(result.get("npc_id"), "jason_it")
        self.assertEqual(result.get("outcome"), "success")
        self.assertNotIn("gremlins", engine.state.player.quests)
        self.assertEqual(engine.state.player.quests[QUEST_ID]["stage"], "purge_crypto_miners")
        self.assertEqual(engine.state.player.quests[QUEST_ID]["counters"]["score"], 1)
        self.assertEqual(result.get("scene"), "SCENE_GREMLINS")

    @patch(
        "quests.literal_gremlins.call_llm_json",
        return_value={
            "success": False,
            "stage_complete": True,
            "flavor": "Jason rewrites the bad answer into a suspiciously good solution.",
            "energy_delta": -4,
            "stress_delta": 4,
        },
    )
    def test_llm_flavor_does_not_replace_authored_stage_text(self, _mock_llm: object) -> None:
        engine = _engine_with_jason()
        engine.state.player.quests["gremlins"] = {"stage": 1, "score": 0}

        result = engine._resolve_socialize(
            npc_id="jason_it",
            player_input="Rotate keys on AWS Secrets",
        )

        self.assertNotIn("suspiciously good solution", result.get("flavor", ""))
        self.assertIn("did not stabilize anything", result.get("flavor", ""))

    @patch("quests.literal_gremlins.call_llm_json", return_value=None)
    def test_quest_steps_do_not_trigger_watercooler_hr_warning(self, _mock_llm: object) -> None:
        engine = _engine_with_jason()

        engine.handle_action("visit_it")
        engine.handle_action(
            "socialize",
            npc_id="jason_it",
            player_input="I will shield the fiber network and reroute damaged cables.",
        )
        engine.handle_action(
            "socialize",
            npc_id="jason_it",
            player_input="Cut SSH tunnel access and quarantine the compromised nodes.",
        )
        engine.handle_action(
            "socialize",
            npc_id="jason_it",
            player_input="Bottleneck the manager with Jira tickets and calendar invites.",
        )

        self.assertEqual(engine.state.player.watercooler_time, 0)
        self.assertEqual(engine.state.player.hr_warnings, [])

    @patch("quests.literal_gremlins.call_llm_json", return_value=None)
    def test_fallback_completion_sets_normal_success_at_two_points(self, _mock_llm: object) -> None:
        engine = _engine_with_jason()
        engine.state.init_relationship(
            npc_id="jason_it",
            name="Jason",
            role="IT Support / Tech Purist",
            pfp="Jason-Basement_IT.png",
            trust=55,
            rivalry=5,
        )
        engine.state.player.quests["gremlins"] = {"stage": 3, "score": 1}

        result = engine._resolve_socialize(
            npc_id="jason_it",
            player_input="We should escalate, evict the manager, and relocate them to Marketing immediately.",
        )

        self.assertEqual(result.get("npc_id"), "jason_it")
        self.assertEqual(result.get("outcome"), "success")
        self.assertEqual(result.get("scene"), "SCENE_IT_BASEMENT")
        self.assertEqual(engine.state.player.quests[QUEST_ID]["status"], "completed")
        self.assertEqual(engine.state.player.skills["engineering"], 3)
        self.assertNotIn("cto_badge", engine.state.player.unlocks)

    @patch("quests.literal_gremlins.call_llm_json", return_value=None)
    def test_fallback_completion_unlocks_cto_badge_at_three_points(self, _mock_llm: object) -> None:
        engine = _engine_with_jason()
        engine.state.init_relationship(
            npc_id="jason_it",
            name="Jason",
            role="IT Support / Tech Purist",
            pfp="Jason-Basement_IT.png",
            trust=55,
            rivalry=5,
        )
        engine.state.player.quests["gremlins"] = {"stage": 3, "score": 2}

        result = engine._resolve_socialize(
            npc_id="jason_it",
            player_input="We should escalate, evict the manager, and relocate them to Marketing immediately.",
        )

        self.assertEqual(result.get("outcome"), "legendary")
        self.assertEqual(result.get("scene"), "SCENE_IT_BASEMENT")
        self.assertEqual(engine.state.player.quests[QUEST_ID]["status"], "completed")
        self.assertEqual(engine.state.player.quests[QUEST_ID]["flags"]["cto_badge_unlocked"], True)
        self.assertEqual(engine.state.player.skills["engineering"], 4)
        self.assertIn("cto_badge", engine.state.player.unlocks)

    @patch("quests.literal_gremlins.call_llm_json", return_value=None)
    def test_fallback_completion_fails_below_two_points(self, _mock_llm: object) -> None:
        engine = _engine_with_jason()
        engine.state.init_relationship(
            npc_id="jason_it",
            name="Jason",
            role="IT Support / Tech Purist",
            pfp="Jason-Basement_IT.png",
            trust=55,
            rivalry=5,
        )
        engine.state.player.quests["gremlins"] = {"stage": 3, "score": 0}

        result = engine._resolve_socialize(
            npc_id="jason_it",
            player_input="Let's schedule a meeting and ignore the fire.",
        )

        self.assertEqual(result.get("outcome"), "failed")
        self.assertEqual(result.get("scene"), "SCENE_RACKS_ON_FIRE")
        self.assertEqual(engine.state.player.quests[QUEST_ID]["status"], "failed")
        self.assertEqual(engine.state.player.quests[QUEST_ID]["stage"], "failed")
        self.assertEqual(engine.state.player.skills["engineering"], 1)
        self.assertNotIn("cto_badge", engine.state.player.unlocks)


if __name__ == "__main__":
    unittest.main()

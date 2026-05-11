from __future__ import annotations

import unittest

from src.systems.adapter import dispatch, list_supported_calls, make_call, response


class AdapterContractTests(unittest.TestCase):
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
        self.snapshot = {
            "department": "technical.middle.backend",
            "relationships": {
                "alex_lead": {"trust": 55, "rivalry": 0},
            },
        }

    def test_make_call_publishes_stable_envelope(self) -> None:
        call = make_call("social_actions", "list")
        self.assertEqual(set(call), {"system", "action", "payload", "player_snapshot", "data", "context"})

    def test_response_normalizes_result_payload(self) -> None:
        payload = response("result", result={"outcome": "excellent", "rep_delta": 3})
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["kind"], "result")
        self.assertEqual(payload["result"]["outcome"], "partial")

    def test_supported_calls_are_visible(self) -> None:
        supported = list_supported_calls()
        self.assertIn("social_actions", supported)
        self.assertIn("execute", supported["social_actions"])

    def test_dispatch_social_action_plan(self) -> None:
        call = make_call(
            "social_actions",
            "plan",
            payload={"social_action": "seek_mentorship", "npc": self.npc},
            player_snapshot=self.snapshot,
        )
        result = dispatch(call)
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "plan")
        self.assertEqual(result["data"]["action"], "seek_mentorship")

    def test_dispatch_social_action_execute_returns_result(self) -> None:
        call = make_call(
            "social_actions",
            "execute",
            payload={"social_action": "relationship_maintenance", "npc": self.npc},
            player_snapshot=self.snapshot,
        )
        result = dispatch(call)
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "result")
        self.assertEqual(result["result"]["outcome"], "success")

    def test_dispatch_rejects_unknown_system(self) -> None:
        result = dispatch(make_call("unknown", "noop"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["kind"], "error")

    def test_watercooler_choose_context_honors_locked_explicit_target(self) -> None:
        npcs = [
            {"id": "sam_coworker", "watercooler_scene": "Watercooler_Personnel_Generic-scene.jpg", "watercooler_seed": "seed"},
            {
                "id": "jason_it",
                "watercooler_scene": "IT-Basement_Bored-Technician.jpeg",
                "watercooler_seed": "Jason in basement",
                "watercooler_pool": False,
            },
        ]
        call = make_call(
            "watercooler",
            "choose_context",
            payload={
                "requested_npc_id": "jason_it",
                "lock_requested_npc": True,
                "npcs": npcs,
                "stress": 100,
            },
        )
        result = dispatch(call)
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "data")
        self.assertEqual(result["data"].get("npc_id"), "jason_it")


if __name__ == "__main__":
    unittest.main()

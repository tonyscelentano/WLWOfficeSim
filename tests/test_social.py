from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from systems.social import resolve_interaction


class SocialFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        # Force fallback by removing API keys from environment
        self.old_nvidia_key = os.environ.pop("NVIDIA_API_KEY", None)
        self.old_nim_key = os.environ.pop("NIM_API_KEY", None)

    def tearDown(self) -> None:
        if self.old_nvidia_key is not None:
            os.environ["NVIDIA_API_KEY"] = self.old_nvidia_key
        if self.old_nim_key is not None:
            os.environ["NIM_API_KEY"] = self.old_nim_key

    def test_cross_cluster_political_npc_is_harder_to_impress(self) -> None:
        npc = {
            "id": "maya_csm",
            "name": "Maya",
            "archetype": "political",
            "cluster": "csm",
            "ambition": 7,
            "influence_weight": 8,
            "base_trust": 50,
        }
        archetype = {"id": "political"}
        player_snapshot = {
            "department": "technical.middle.backend",
            "skills": {"communication": 4},
            "relationships": {"maya_csm": {"trust": 50, "rivalry": 0}},
        }
        result = resolve_interaction(npc, archetype, "We should align on client outcomes.", player_snapshot)
        self.assertIn(result["outcome"], {"partial", "dumpster_fire"})

    def test_same_cluster_mentor_can_succeed_with_moderate_comm_skill(self) -> None:
        npc = {
            "id": "eli_arch",
            "name": "Eli",
            "archetype": "mentor",
            "cluster": "backend",
            "ambition": 5,
            "influence_weight": 5,
            "base_trust": 45,
        }
        archetype = {"id": "mentor"}
        player_snapshot = {
            "department": "technical.middle.backend",
            "skills": {"communication": 6},
            "relationships": {"eli_arch": {"trust": 65, "rivalry": 0}},
        }
        result = resolve_interaction(npc, archetype, "Can you help me think through the tradeoffs?", player_snapshot)
        self.assertEqual(result["outcome"], "success")
        self.assertGreaterEqual(result["npc_deltas"]["eli_arch"]["trust"], 0)


if __name__ == "__main__":
    unittest.main()

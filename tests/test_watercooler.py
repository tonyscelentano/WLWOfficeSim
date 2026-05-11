from __future__ import annotations

import random
import unittest

from src.systems.watercooler import choose_watercooler_context, resolve_watercooler_npc_id


NPCS = [
    {"id": "alex_lead", "watercooler_scene": "Watercooler_Personnel_Generic-scene.jpg", "watercooler_seed": "seed"},
    {"id": "sam_coworker", "watercooler_scene": "Watercooler_Personnel_Generic-scene.jpg", "watercooler_seed": "seed"},
    {"id": "root_devops_cat", "watercooler_scene": "Watercooler_Personnel_Generic-DevOpsCat.jpeg", "watercooler_seed": "seed"},
    {"id": "diane_gossip", "watercooler_scene": "Watercooler_Personnel_Generic-GossipGirls.jpeg", "watercooler_seed": "Diane"},
    {"id": "nina_hr", "watercooler_scene": "Watercooler_Personnel_Generic-scene.jpg", "watercooler_seed": "seed"},
    {"id": "iris_it", "watercooler_scene": "Watercooler_Personnel_Generic-scene.jpg", "watercooler_seed": "seed"},
    {
        "id": "jason_it",
        "watercooler_scene": "IT-Basement_Bored-Technician.jpeg",
        "watercooler_seed": "Jason in the basement.",
        "watercooler_pool": False,
    },
]


class WatercoolerTests(unittest.TestCase):
    def test_alias_resolves_to_depicted_npc(self) -> None:
        self.assertEqual(resolve_watercooler_npc_id("hr_partner", NPCS), "nina_hr")
        self.assertEqual(resolve_watercooler_npc_id("random_dev", NPCS), "iris_it")

    def test_high_stress_routes_to_devops_scene_before_chat(self) -> None:
        context = choose_watercooler_context("alex_lead", NPCS, stress=90)
        self.assertEqual(context["npc_id"], "root_devops_cat")
        self.assertEqual(context["scene"], "Watercooler_Personnel_Generic-DevOpsCat.jpeg")

    def test_requested_npc_keeps_matching_scene(self) -> None:
        context = choose_watercooler_context("diane_gossip", NPCS)
        self.assertEqual(context["scene"], "Watercooler_Personnel_Generic-GossipGirls.jpeg")
        self.assertIn("Diane", context["seed"])

    def test_locked_explicit_target_keeps_requested_npc_even_if_not_in_pool(self) -> None:
        context = choose_watercooler_context("jason_it", NPCS, lock_requested_npc=True, stress=99)
        self.assertEqual(context["npc_id"], "jason_it")
        self.assertEqual(context["scene"], "IT-Basement_Bored-Technician.jpeg")

    def test_alias_resolves_when_explicit_target_is_locked(self) -> None:
        npc_id = resolve_watercooler_npc_id("hr_partner", NPCS, lock_requested_npc=True)
        self.assertEqual(npc_id, "nina_hr")

    def test_unknown_request_picks_available_watercooler_npc(self) -> None:
        context = choose_watercooler_context("not_real", NPCS, rng=random.Random(3))
        self.assertIn(context["npc_id"], {npc["id"] for npc in NPCS})
        self.assertTrue(context["scene"].startswith("Watercooler_Personnel_Generic-"))


if __name__ == "__main__":
    unittest.main()

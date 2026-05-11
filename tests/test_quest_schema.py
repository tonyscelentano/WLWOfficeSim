from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.state import GameState
from quests.definition import (
    QuestDefinitionError,
    load_all_quest_definitions,
    load_quest_definition,
    validate_quest_definition,
)
from quests.registry import QuestRegistry
from quests.schema import QuestProgress, QuestProgressError


class QuestSchemaTests(unittest.TestCase):
    def test_schema_json_files_are_valid_json(self) -> None:
        schema_dir = Path("src/quests/schemas")
        for path in schema_dir.glob("*.schema.json"):
            with self.subTest(path=path):
                json.loads(path.read_text(encoding="utf-8"))

    def test_literal_gremlins_definition_loads_and_validates(self) -> None:
        definition = load_quest_definition("literal_gremlins")

        self.assertEqual(definition["quest_id"], "literal_gremlins")
        self.assertIn(definition["initial_stage"], definition["stages"])
        self.assertEqual(definition["completion"]["success_min_score"], 2)
        self.assertEqual(definition["completion"]["legendary_min_score"], 3)
        self.assertEqual(definition["rewards"]["legendary"]["min_score"], 3)
        self.assertEqual(definition["rewards"]["success"]["skill_deltas"]["engineering"], 2)

    def test_all_enabled_quest_definitions_load_by_id(self) -> None:
        definitions = load_all_quest_definitions()

        self.assertIn("literal_gremlins", definitions)
        self.assertEqual(definitions["literal_gremlins"]["status"], "enabled")

    def test_quest_definition_rejects_unknown_keys(self) -> None:
        definition = load_quest_definition("literal_gremlins")
        definition["surprise"] = True

        with self.assertRaises(QuestDefinitionError):
            validate_quest_definition(definition)

    def test_quest_definition_rejects_broken_stage_link(self) -> None:
        definition = load_quest_definition("literal_gremlins")
        definition["stages"]["stabilize_racks"]["next_stage"] = "missing_stage"

        with self.assertRaises(QuestDefinitionError):
            validate_quest_definition(definition)

    def test_quest_progress_round_trips_strict_shape(self) -> None:
        progress = QuestProgress(
            quest_id="literal_gremlins",
            status="active",
            stage="stabilize_racks",
            flags={"cto_badge_unlocked": False},
            counters={"score": 0, "attempts": 0},
            variables={},
        )

        self.assertEqual(QuestProgress.from_dict(progress.to_dict()).to_dict(), progress.to_dict())

    def test_quest_progress_rejects_extra_keys(self) -> None:
        raw = {
            "quest_id": "literal_gremlins",
            "status": "active",
            "stage": "stabilize_racks",
            "flags": {},
            "counters": {},
            "variables": {},
            "version": 1,
            "extra": True,
        }

        with self.assertRaises(QuestProgressError):
            QuestProgress.from_dict(raw)

    def test_registry_routes_social_event_to_enabled_quest(self) -> None:
        state = GameState()
        data = {
            "npcs": [
                {
                    "id": "jason_it",
                    "name": "Jason",
                    "role": "IT Support",
                    "pfp": None,
                    "base_trust": 50,
                    "base_rivalry": 0,
                }
            ]
        }

        result = QuestRegistry(state, data).handle_event(
            "social",
            {
                "npc_id": "jason_it",
                "player_input": "",
                "force_offer": True,
            },
        )

        self.assertIsNotNone(result)
        self.assertIn("literal_gremlins", state.player.quests)


if __name__ == "__main__":
    unittest.main()

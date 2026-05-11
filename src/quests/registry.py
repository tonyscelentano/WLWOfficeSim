from __future__ import annotations

from typing import Any

from core.state import GameState
from quests.definition import load_all_quest_definitions
from quests.literal_gremlins import QUEST_ID as LITERAL_GREMLINS_ID
from quests.literal_gremlins import LiteralGremlinsQuest


QUEST_HANDLERS = {
    LITERAL_GREMLINS_ID: LiteralGremlinsQuest,
}


class QuestRegistry:
    def __init__(self, state: GameState, data: dict[str, Any]) -> None:
        self.state = state
        self.data = data
        self.definitions = load_all_quest_definitions()

    def handle_event(self, event_type: str, payload: dict[str, Any]) -> dict | None:
        for quest_id, definition in self.definitions.items():
            handler_cls = QUEST_HANDLERS.get(quest_id)
            if handler_cls is None:
                continue
            result = handler_cls(self.state, self.data, definition=definition).handle_event(event_type, payload)
            if result is not None:
                return result
        return None

    def handle_social(
        self,
        npc_id: str,
        player_input: str,
        force_offer: bool = False,
    ) -> dict | None:
        return self.handle_event(
            "social",
            {
                "npc_id": npc_id,
                "player_input": player_input,
                "force_offer": force_offer,
            },
        )

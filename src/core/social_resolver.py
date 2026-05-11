from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from core.bus import bus
from core.state import GameState
from quests.registry import QuestRegistry
from systems import adapter


class SocialResolver:
    def __init__(
        self,
        state: GameState,
        data: dict[str, Any],
        strings: Callable[..., str],
    ) -> None:
        self.state = state
        self.data = data
        self._s = strings

    def resolve(
        self,
        npc_id: str,
        player_input: str = "",
        force_quest_offer: bool = False,
    ) -> dict:
        discovered_npcs = [
            n_id for n_id, rel in self.state.player.relationships.items()
            if rel.name != "Unknown"
        ]

        ctx_response = adapter.dispatch({
            "system": "watercooler",
            "action": "choose_context",
            "payload": {
                "requested_npc_id": npc_id,
                "lock_requested_npc": bool(str(npc_id or "").strip()),
                "npcs": self.data.get("npcs", []),
                "stress": self.state.player.stress,
                "player_input": player_input,
                "discovered_npcs": discovered_npcs,
            },
        })
        watercooler_context = ctx_response.get("data", {})
        effective_npc_id = watercooler_context.get("npc_id", npc_id)

        npc_template = self._find_npc(effective_npc_id)
        if npc_template is None:
            return {"outcome": "error", "flavor": f"NPC '{effective_npc_id}' not found."}

        quest_result = QuestRegistry(self.state, self.data).handle_social(
            effective_npc_id,
            player_input,
            force_offer=force_quest_offer,
        )
        if quest_result is not None:
            return quest_result

        self._track_watercooler_time()

        self._sync_relationship(effective_npc_id, npc_template)

        effective_input = player_input or watercooler_context.get("seed", "")
        archetype_data = self.data.get("interactions", {}).get(npc_template.get("archetype", ""), {})

        interaction_response = adapter.dispatch({
            "system": "social",
            "action": "resolve_interaction",
            "payload": {
                "npc": npc_template,
                "archetype": archetype_data,
                "player_input": effective_input,
            },
            "player_snapshot": self.state.snapshot(),
        })
        result = interaction_response.get("result") or {"outcome": "error", "flavor": self._s("engine", "adapter_error")}

        self._append_social_log(player_input, npc_template, result)
        self._apply_dynamic_context(result, effective_npc_id, player_input)

        bus.publish("social_resolved", {
            "npc_id": effective_npc_id,
            "outcome": result.get("outcome"),
        })
        return result

    def _sync_relationship(self, npc_id: str, npc_template: dict[str, Any]) -> None:
        rel = self.state.player.relationships.get(npc_id)
        if not rel:
            self.state.init_relationship(
                npc_id=npc_id,
                name=npc_template.get("name", "Unknown"),
                role=npc_template.get("role", "Unknown"),
                pfp=npc_template.get("pfp"),
                trust=npc_template.get("base_trust", 50),
                rivalry=npc_template.get("base_rivalry", 0),
            )
            return

        rel.name = npc_template.get("name", "Unknown")
        rel.role = npc_template.get("role", "Unknown")
        rel.pfp = npc_template.get("pfp")

    def _append_social_log(self, player_input: str, npc_template: dict[str, Any], result: dict) -> None:
        self.state.player.social_log.append({
            "role": "player",
            "name": self.state.player.name,
            "text": player_input,
            "timestamp": datetime.now().isoformat(),
        })
        self.state.player.social_log.append({
            "role": "npc",
            "name": npc_template.get("name", "Unknown"),
            "text": result.get("flavor", ""),
            "timestamp": datetime.now().isoformat(),
        })

    def _apply_dynamic_context(self, result: dict, npc_id: str, player_input: str) -> None:
        post_ctx_response = adapter.dispatch({
            "system": "watercooler",
            "action": "context_for_npc",
            "payload": {
                "npc_id": npc_id,
                "npcs": self.data.get("npcs", []),
                "last_outcome": result.get("outcome", "partial"),
                "player_input": player_input,
            },
        })
        dynamic_context = post_ctx_response.get("data", {})
        result["scene"] = dynamic_context.get("scene", "SCENE_WATERCOOLER")
        result["npc_id"] = npc_id

    def _track_watercooler_time(self) -> None:
        self.state.player.watercooler_time += 15
        if self.state.player.watercooler_time >= 60:
            self.state.add_hr_warning("Efficiency Notice: Excessive non-work socializing detected. Please return to cubicle.")

    def _find_npc(self, npc_id: str) -> dict[str, Any] | None:
        return next((npc for npc in self.data["npcs"] if npc["id"] == npc_id), None)

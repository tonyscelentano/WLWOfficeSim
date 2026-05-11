from __future__ import annotations

from typing import Any

from core.state import GameState
from quests.schema import QuestProgress


def apply_quest_reward(
    state: GameState,
    progress: QuestProgress,
    reward: dict[str, Any],
) -> None:
    for npc_id, deltas in reward.get("relationship", {}).items():
        state.update_relationship(
            npc_id,
            trust_delta=int(deltas.get("trust", 0)),
            rivalry_delta=int(deltas.get("rivalry", 0)),
        )

    state.apply_delta({key: int(value) for key, value in reward.get("stats", {}).items()})

    for skill, delta in reward.get("skill_deltas", {}).items():
        state.apply_skill_delta(str(skill), int(delta))

    for unlock in reward.get("unlocks", []):
        if unlock not in state.player.unlocks:
            state.player.unlocks.append(unlock)

    for flag, value in reward.get("flags", {}).items():
        progress.flags[flag] = bool(value)

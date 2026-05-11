from __future__ import annotations

from collections.abc import Iterable

from core.state import GameState
from quests.schema import QuestProgress


class QuestManager:
    def __init__(self, state: GameState) -> None:
        self.state = state

    def get(self, quest_id: str) -> QuestProgress | None:
        raw = self.state.player.quests.get(quest_id)
        if not isinstance(raw, dict):
            return None
        try:
            return QuestProgress.from_dict(raw)
        except (TypeError, ValueError):
            return None

    def save(self, progress: QuestProgress) -> QuestProgress:
        self.state.player.quests[progress.quest_id] = progress.to_dict()
        return progress

    def start(
        self,
        quest_id: str,
        stage: str,
        flags: dict[str, bool] | None = None,
        counters: dict[str, int] | None = None,
        variables: dict | None = None,
    ) -> QuestProgress:
        progress = QuestProgress(
            quest_id=quest_id,
            status="active",
            stage=stage,
            flags=flags or {},
            counters=counters or {},
            variables=variables or {},
        )
        return self.save(progress)

    def complete(self, progress: QuestProgress) -> QuestProgress:
        progress.status = "completed"
        return self.save(progress)

    def fail(self, progress: QuestProgress) -> QuestProgress:
        progress.status = "failed"
        return self.save(progress)

    def remove_legacy_keys(self, keys: Iterable[str]) -> None:
        for key in keys:
            self.state.player.quests.pop(key, None)

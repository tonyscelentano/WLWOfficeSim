from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quests.definition import QUEST_ID_PATTERN


VALID_STATUSES = {"locked", "available", "active", "completed", "failed"}
PROGRESS_KEYS = {"quest_id", "status", "stage", "flags", "counters", "variables", "version"}


class QuestProgressError(ValueError):
    pass


@dataclass
class QuestProgress:
    quest_id: str
    status: str
    stage: str
    flags: dict[str, bool] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def __post_init__(self) -> None:
        if not self.quest_id or not isinstance(self.quest_id, str) or not QUEST_ID_PATTERN.fullmatch(self.quest_id):
            raise QuestProgressError("Quest progress requires a lowercase slug quest_id.")
        if self.status not in VALID_STATUSES:
            raise QuestProgressError(f"Invalid quest status {self.status!r}.")
        if not self.stage or not isinstance(self.stage, str):
            raise QuestProgressError("Quest progress requires a non-empty stage.")

        self.flags = _validate_flags(self.flags)
        self.counters = _validate_counters(self.counters)
        if not isinstance(self.variables, dict) or not _is_json_safe(self.variables):
            raise QuestProgressError("Quest variables must be a JSON-safe object.")
        self.variables = dict(self.variables or {})
        if type(self.version) is not int or self.version < 1:
            raise QuestProgressError("Quest progress version must be an integer >= 1.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "status": self.status,
            "stage": self.stage,
            "flags": dict(self.flags),
            "counters": dict(self.counters),
            "variables": dict(self.variables),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestProgress":
        if not isinstance(data, dict):
            raise QuestProgressError("Quest progress must be an object.")
        actual = set(data)
        if actual != PROGRESS_KEYS:
            missing = sorted(PROGRESS_KEYS - actual)
            extra = sorted(actual - PROGRESS_KEYS)
            raise QuestProgressError(f"Quest progress keys mismatch. Missing={missing} Extra={extra}")
        if not isinstance(data["quest_id"], str):
            raise QuestProgressError("Quest progress quest_id must be a string.")
        if not isinstance(data["status"], str):
            raise QuestProgressError("Quest progress status must be a string.")
        if not isinstance(data["stage"], str):
            raise QuestProgressError("Quest progress stage must be a string.")
        return cls(
            quest_id=data["quest_id"].strip(),
            status=data["status"].strip(),
            stage=data["stage"].strip(),
            flags=dict(data["flags"]),
            counters=dict(data["counters"]),
            variables=dict(data["variables"]),
            version=data["version"],
        )


def _validate_flags(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        raise QuestProgressError("Quest flags must be an object.")
    result: dict[str, bool] = {}
    for key, flag in value.items():
        if not isinstance(key, str) or not QUEST_ID_PATTERN.fullmatch(key):
            raise QuestProgressError("Quest flag keys must be lowercase slugs.")
        if type(flag) is not bool:
            raise QuestProgressError(f"Quest flag {key!r} must be boolean.")
        result[key] = flag
    return result


def _validate_counters(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        raise QuestProgressError("Quest counters must be an object.")
    result: dict[str, int] = {}
    for key, counter in value.items():
        if not isinstance(key, str) or not QUEST_ID_PATTERN.fullmatch(key):
            raise QuestProgressError("Quest counter keys must be lowercase slugs.")
        if type(counter) is not int:
            raise QuestProgressError(f"Quest counter {key!r} must be integer.")
        result[key] = counter
    return result


def _is_json_safe(value: Any) -> bool:
    if value is None or type(value) in {str, int, float, bool}:
        return True
    if isinstance(value, list):
        return all(_is_json_safe(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_safe(item) for key, item in value.items())
    return False

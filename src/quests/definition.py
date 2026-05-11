from __future__ import annotations

import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any


QUEST_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
TERMINAL_STAGES = {"completed", "failed"}
DEFINITION_DIR = Path(__file__).resolve().parent / "definitions"
ALLOWED_ENTRYPOINT_TYPES = {"social", "work", "event"}
ALLOWED_START_OUTCOMES = {"success", "partial", "blocked", "error"}
ALLOWED_REWARD_STATS = {"energy", "stress", "reputation", "money", "xp"}


class QuestDefinitionError(ValueError):
    pass


def load_quest_definition(quest_id: str) -> dict[str, Any]:
    return deepcopy(_load_quest_definition_cached(quest_id))


def load_all_quest_definitions(include_disabled: bool = False) -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    for path in sorted(DEFINITION_DIR.glob("*.quest.json")):
        quest_id = path.name.removesuffix(".quest.json")
        definition = load_quest_definition(quest_id)
        if include_disabled or definition["status"] == "enabled":
            definitions[quest_id] = definition
    return definitions


@lru_cache(maxsize=None)
def _load_quest_definition_cached(quest_id: str) -> dict[str, Any]:
    _require_slug(quest_id, "quest_id")
    path = DEFINITION_DIR / f"{quest_id}.quest.json"
    with path.open(encoding="utf-8") as file:
        definition = json.load(file)
    validate_quest_definition(definition)
    if definition["quest_id"] != quest_id:
        raise QuestDefinitionError(f"{path.name}: quest_id does not match filename.")
    return definition


def validate_quest_definition(definition: dict[str, Any]) -> None:
    _require_exact_keys(
        definition,
        {
            "quest_id",
            "title",
            "version",
            "status",
            "entrypoints",
            "initial_stage",
            "start_result",
            "stages",
            "completion",
            "rewards",
        },
        "quest definition",
    )
    _require_slug(definition["quest_id"], "quest_id")
    _require_nonempty_string(definition["title"], "title")
    _require_int(definition["version"], "version", minimum=1)
    if definition["status"] not in {"enabled", "disabled"}:
        raise QuestDefinitionError("status must be enabled or disabled.")

    stages = _require_dict(definition["stages"], "stages")
    if not stages:
        raise QuestDefinitionError("stages must contain at least one stage.")
    initial_stage = _require_nonempty_string(definition["initial_stage"], "initial_stage")
    if initial_stage not in stages:
        raise QuestDefinitionError("initial_stage must exist in stages.")

    _validate_entrypoints(definition["entrypoints"])
    _validate_start_result(definition["start_result"])
    _validate_stages(stages)
    _validate_completion(definition["completion"])
    _validate_rewards(definition["rewards"])


def _validate_entrypoints(entrypoints: Any) -> None:
    if not isinstance(entrypoints, list) or not entrypoints:
        raise QuestDefinitionError("entrypoints must be a non-empty array.")
    for index, entrypoint in enumerate(entrypoints):
        label = f"entrypoints[{index}]"
        entrypoint = _require_dict(entrypoint, label)
        allowed = {"type", "npc_id", "triggers", "allow_empty_forced_offer"}
        _require_subset_keys(entrypoint, allowed, label)
        entry_type = entrypoint.get("type")
        if entry_type not in ALLOWED_ENTRYPOINT_TYPES:
            raise QuestDefinitionError(f"{label}.type is invalid.")
        if entry_type == "social":
            _require_slug(entrypoint.get("npc_id"), f"{label}.npc_id")
        if "triggers" in entrypoint:
            _require_unique_string_list(entrypoint["triggers"], f"{label}.triggers", allow_empty=False)
        if "allow_empty_forced_offer" in entrypoint and type(entrypoint["allow_empty_forced_offer"]) is not bool:
            raise QuestDefinitionError(f"{label}.allow_empty_forced_offer must be boolean.")


def _validate_start_result(start_result: Any) -> None:
    start_result = _require_dict(start_result, "start_result")
    _require_exact_keys(start_result, {"outcome", "flavor", "scene"}, "start_result")
    if start_result["outcome"] not in ALLOWED_START_OUTCOMES:
        raise QuestDefinitionError("start_result.outcome is invalid.")
    _require_nonempty_string(start_result["flavor"], "start_result.flavor")
    _require_nonempty_string(start_result["scene"], "start_result.scene")


def _validate_stages(stages: dict[str, Any]) -> None:
    seen_orders: set[int] = set()
    for stage_id, stage in stages.items():
        _require_slug(stage_id, f"stage id {stage_id!r}")
        stage = _require_dict(stage, f"stages.{stage_id}")
        _require_exact_keys(
            stage,
            {
                "order",
                "prompt_stage",
                "briefing",
                "objective",
                "success_cues",
                "failure_cues",
                "success_flavor",
                "failure_flavor",
                "coaching",
                "next_stage",
            },
            f"stages.{stage_id}",
        )
        order = _require_int(stage["order"], f"stages.{stage_id}.order", minimum=1)
        if order in seen_orders:
            raise QuestDefinitionError(f"Duplicate stage order {order}.")
        seen_orders.add(order)
        _require_int(stage["prompt_stage"], f"stages.{stage_id}.prompt_stage", minimum=1)
        _require_nonempty_string(stage["briefing"], f"stages.{stage_id}.briefing")
        _require_nonempty_string(stage["objective"], f"stages.{stage_id}.objective")
        _require_unique_string_list(stage["success_cues"], f"stages.{stage_id}.success_cues", allow_empty=False)
        _require_unique_string_list(stage["failure_cues"], f"stages.{stage_id}.failure_cues", allow_empty=True)
        _require_nonempty_string(stage["success_flavor"], f"stages.{stage_id}.success_flavor")
        _require_nonempty_string(stage["failure_flavor"], f"stages.{stage_id}.failure_flavor")
        _require_nonempty_string(stage["coaching"], f"stages.{stage_id}.coaching")
        next_stage = _require_nonempty_string(stage["next_stage"], f"stages.{stage_id}.next_stage")
        if next_stage not in stages and next_stage not in TERMINAL_STAGES:
            raise QuestDefinitionError(f"stages.{stage_id}.next_stage must reference a stage or terminal stage.")


def _validate_completion(completion: Any) -> None:
    completion = _require_dict(completion, "completion")
    _require_exact_keys(
        completion,
        {
            "success_min_score",
            "legendary_min_score",
            "active_scene",
            "success_scene",
            "failure_scene",
        },
        "completion",
    )
    success_min = _require_int(completion["success_min_score"], "completion.success_min_score", minimum=0)
    legendary_min = _require_int(completion["legendary_min_score"], "completion.legendary_min_score", minimum=0)
    if legendary_min < success_min:
        raise QuestDefinitionError("completion.legendary_min_score must be >= success_min_score.")
    _require_nonempty_string(completion["active_scene"], "completion.active_scene")
    _require_nonempty_string(completion["success_scene"], "completion.success_scene")
    _require_nonempty_string(completion["failure_scene"], "completion.failure_scene")


def _validate_rewards(rewards: Any) -> None:
    rewards = _require_dict(rewards, "rewards")
    _require_exact_keys(rewards, {"failure", "success", "legendary"}, "rewards")
    _validate_reward(rewards["failure"], "rewards.failure", require_min_score=False)
    _validate_reward(rewards["success"], "rewards.success", require_min_score=False)
    _validate_reward(rewards["legendary"], "rewards.legendary", require_min_score=True)


def _validate_reward(reward: Any, label: str, require_min_score: bool) -> None:
    reward = _require_dict(reward, label)
    allowed = {"relationship", "stats", "skill_deltas", "unlocks", "flags", "flavor_append"}
    if require_min_score:
        allowed.add("min_score")
    _require_exact_keys(reward, allowed, label)
    if require_min_score:
        _require_int(reward["min_score"], f"{label}.min_score", minimum=0)

    relationships = _require_dict(reward["relationship"], f"{label}.relationship")
    for npc_id, deltas in relationships.items():
        _require_slug(npc_id, f"{label}.relationship npc_id")
        deltas = _require_dict(deltas, f"{label}.relationship.{npc_id}")
        _require_subset_keys(deltas, {"trust", "rivalry"}, f"{label}.relationship.{npc_id}")
        for key, value in deltas.items():
            _require_int(value, f"{label}.relationship.{npc_id}.{key}")

    stats = _require_dict(reward["stats"], f"{label}.stats")
    _require_subset_keys(stats, ALLOWED_REWARD_STATS, f"{label}.stats")
    for key, value in stats.items():
        _require_int(value, f"{label}.stats.{key}")

    skill_deltas = _require_dict(reward["skill_deltas"], f"{label}.skill_deltas")
    for key, value in skill_deltas.items():
        _require_slug(key, f"{label}.skill_deltas key")
        _require_int(value, f"{label}.skill_deltas.{key}")

    _require_unique_string_list(reward["unlocks"], f"{label}.unlocks", allow_empty=True)
    flags = _require_dict(reward["flags"], f"{label}.flags")
    for key, value in flags.items():
        _require_slug(key, f"{label}.flags key")
        if type(value) is not bool:
            raise QuestDefinitionError(f"{label}.flags.{key} must be boolean.")
    if not isinstance(reward["flavor_append"], str):
        raise QuestDefinitionError(f"{label}.flavor_append must be a string.")


def _require_exact_keys(data: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(data)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise QuestDefinitionError(f"{label} keys mismatch. Missing={missing} Extra={extra}")


def _require_subset_keys(data: dict[str, Any], allowed: set[str], label: str) -> None:
    extra = sorted(set(data) - allowed)
    if extra:
        raise QuestDefinitionError(f"{label} has unknown keys: {extra}")


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QuestDefinitionError(f"{label} must be an object.")
    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuestDefinitionError(f"{label} must be a non-empty string.")
    return value


def _require_slug(value: Any, label: str) -> str:
    value = _require_nonempty_string(value, label)
    if not QUEST_ID_PATTERN.fullmatch(value):
        raise QuestDefinitionError(f"{label} must be a lowercase slug.")
    return value


def _require_int(value: Any, label: str, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise QuestDefinitionError(f"{label} must be an integer.")
    if minimum is not None and value < minimum:
        raise QuestDefinitionError(f"{label} must be >= {minimum}.")
    return value


def _require_unique_string_list(value: Any, label: str, allow_empty: bool) -> list[str]:
    if not isinstance(value, list):
        raise QuestDefinitionError(f"{label} must be an array.")
    if not allow_empty and not value:
        raise QuestDefinitionError(f"{label} must not be empty.")
    seen: set[str] = set()
    for item in value:
        text = _require_nonempty_string(item, label)
        if text in seen:
            raise QuestDefinitionError(f"{label} contains duplicate value {text!r}.")
        seen.add(text)
    return value

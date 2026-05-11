"""
career.py — Career progression and office-politics scaffolding

Pure logic only. This module does not mutate state or subscribe directly to the bus.
Engine or a future orchestration layer can call these helpers when bus events fire.
"""
from __future__ import annotations

from typing import Any, Mapping

import tomllib
from pathlib import Path
from functools import lru_cache

from .result_contract import empty_result

DATA_DIR = Path(__file__).parent.parent / "data"
STRINGS_FILE = DATA_DIR / "strings.toml"

@lru_cache(maxsize=1)
def _load_strings() -> dict[str, Any]:
    if not STRINGS_FILE.exists():
        return {}
    with STRINGS_FILE.open("rb") as f:
        return tomllib.load(f)

def _s(key: str, default: str = "", **kwargs: Any) -> str:
    tmpl = _load_strings().get("career", {}).get(key, default)
    try:
        return tmpl.format(**kwargs)
    except Exception:
        return tmpl

SKILL_CEILING = 20
SUBSCRIBED_EVENTS = (
    "task_failed",
    "task_resolved",
    "presence_trait_updated",
    "random_politics",
)

PROMOTION_THRESHOLDS = {
    "manager_trust": 75,
    "reputation": 60,
    "xp": 100,
}

PRESENCE_TRAIT_EFFECTS = {
    "never_leaves": {
        "stress_delta": 8,
        "rep_delta": 4,
        "string_key": "badge_opinions",
    },
    "overachiever": {
        "stress_delta": 4,
        "rep_delta": 3,
        "string_key": "visible_consistency",
    },
    "solid_nine_to_five": {
        "stress_delta": -2,
        "rep_delta": 1,
        "string_key": "stable_hire",
    },
    "ghost": {
        "stress_delta": 2,
        "rep_delta": -4,
        "string_key": "org_chart_ghost",
    },
}

POLITICS_EVENT_EFFECTS = {
    "layoff_rumors": {
        "stress_delta": 25,
        "string_key": "layoff_rumors",
    },
    "surprise_all_hands": {
        "energy_delta": -15,
        "stress_delta": 4,
        "string_key": "all_hands_nothing",
    },
    "prod_outage": {
        "energy_delta": -10,
        "stress_delta": 18,
        "rep_delta": -2,
        "string_key": "production_sounds",
    },
    "executive_spotlight": {
        "stress_delta": 10,
        "rep_delta": 8,
        "string_key": "executive_spotlight",
    },
}


def _copy_result(template: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(template)
    copied["skill_deltas"] = dict(template.get("skill_deltas", {}))
    copied["npc_deltas"] = dict(template.get("npc_deltas", {}))
    return copied


def _relationships_from_snapshot(player_snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw_relationships = player_snapshot.get("relationships", {})
    if not isinstance(raw_relationships, Mapping):
        return {}
    normalized: dict[str, Mapping[str, Any]] = {}
    for npc_id, payload in raw_relationships.items():
        if isinstance(payload, Mapping):
            normalized[str(npc_id)] = payload
    return normalized


def check_promotion_eligibility(player_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """
    Determine whether the player is promotion-eligible.
    """
    manager_id = player_snapshot.get("reports_to")
    if not manager_id:
        return {
            "eligible": False,
            "reason": _s("free_agent_promotion"),
            "blockers": ["missing_manager"],
            "metrics": {},
        }

    relationships = _relationships_from_snapshot(player_snapshot)
    manager = relationships.get(str(manager_id), {})
    metrics = {
        "manager_trust": int(manager.get("trust", 0)),
        "reputation": int(player_snapshot.get("reputation", 0)),
        "xp": int(player_snapshot.get("xp", 0)),
    }

    blockers: list[str] = []
    for key, threshold in PROMOTION_THRESHOLDS.items():
        if metrics[key] < threshold:
            blockers.append(key)

    if blockers:
        blocker_names = ", ".join(blockers)
        return {
            "eligible": False,
            "reason": _s("promotion_signals", blockers=blocker_names),
            "blockers": blockers,
            "metrics": metrics,
        }

    return {
        "eligible": True,
        "reason": _s("promotion_justified"),
        "blockers": [],
        "metrics": metrics,
    }


def apply_promotion(player_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Return a generic promotion bump."""
    title = str(player_snapshot.get("title", "Employee"))
    return {
        "outcome": "success",
        "flavor": _s("promotion_success", title=title),
        "energy_delta": 0,
        "stress_delta": 10,
        "rep_delta": 20,
        "money_delta": 1000,
        "xp_delta": 50,
        "skill_deltas": {},
        "npc_deltas": {},
    }


def _task_failed_effect(event_data: Mapping[str, Any]) -> dict[str, Any]:
    result = empty_result()
    outcome = str(event_data.get("outcome", "")).strip()
    if outcome == "dumpster_fire":
        result["stress_delta"] = 15
        result["rep_delta"] = -5
        result["flavor"] = _s("task_dumpster_fire")
        return result

    result["stress_delta"] = 8
    result["rep_delta"] = -3
    result["flavor"] = _s("task_missed_deadline")
    return result


def _task_resolved_effect(event_data: Mapping[str, Any]) -> dict[str, Any] | None:
    outcome = str(event_data.get("outcome", "")).strip()
    if outcome == "legendary":
        result = empty_result()
        result["rep_delta"] = 6
        result["xp_delta"] = 10
        result["flavor"] = _s("task_legendary")
        return result
    if outcome == "success":
        result = empty_result()
        result["rep_delta"] = 2
        result["flavor"] = _s("task_success")
        return result
    return None


def _presence_trait_effect(event_data: Mapping[str, Any]) -> dict[str, Any] | None:
    trait = str(event_data.get("trait", "")).strip()
    effect = PRESENCE_TRAIT_EFFECTS.get(trait)
    if not effect:
        return None
    result = empty_result()
    result.update({k: v for k, v in effect.items() if k != "string_key"})
    result["flavor"] = _s(effect["string_key"])
    return result


def _politics_effect(event_data: Mapping[str, Any]) -> dict[str, Any] | None:
    politics_type = str(event_data.get("type", "")).strip()
    effect = POLITICS_EVENT_EFFECTS.get(politics_type)
    if not effect:
        return None
    result = empty_result()
    result.update({k: v for k, v in effect.items() if k != "string_key"})
    result["flavor"] = _s(effect["string_key"])
    return result


def handle_bus_event(
    event_name: str,
    event_data: Mapping[str, Any],
    player_snapshot: Mapping[str, Any],
) -> dict[str, Any] | None:
    """
    Pure logic handler for downstream career/politics effects triggered by bus events.
    """
    if event_name not in SUBSCRIBED_EVENTS:
        return None

    handlers = {
        "task_failed": _task_failed_effect,
        "task_resolved": _task_resolved_effect,
        "presence_trait_updated": _presence_trait_effect,
        "random_politics": _politics_effect,
    }
    handler = handlers[event_name]
    result = handler(event_data)
    if result is None:
        return None

    # Free agents should not receive factional promotion-adjacent boosts yet.
    if event_name == "presence_trait_updated" and not player_snapshot.get("reports_to"):
        downgraded = _copy_result(result)
        downgraded["rep_delta"] = min(0, int(downgraded.get("rep_delta", 0)))
        return downgraded

    return result

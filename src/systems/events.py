"""
events.py — Event-system scaffolding

Pure helpers for filtering and resolving office events. This module is deliberately
loader-agnostic so engine integration can happen later without forcing changes to
the event selection logic.
"""
from __future__ import annotations

import random
from typing import Any, Iterable, Mapping

from .result_contract import empty_result

DEFAULT_WEIGHT = 1


def normalize_event_template(raw_event: Mapping[str, Any]) -> dict[str, Any]:
    """
    Normalize a raw event template into a predictable runtime shape.
    The schema is intentionally forgiving so content work can proceed before strict
    validation is wired into loader.py.
    """
    effects = raw_event.get("effects", {})
    if not isinstance(effects, Mapping):
        effects = {}

    normalized = {
        "id": str(raw_event.get("id", "")).strip(),
        "title": str(raw_event.get("title", "Untitled Event")).strip(),
        "type": str(raw_event.get("type", "generic")).strip(),
        "weight": int(raw_event.get("weight", DEFAULT_WEIGHT)),
        "min_day": int(raw_event.get("min_day", 1)),
        "max_day": int(raw_event.get("max_day", 9999)),
        "min_stress": int(raw_event.get("min_stress", 0)),
        "max_stress": int(raw_event.get("max_stress", 100)),
        "department": str(raw_event.get("department", "")).strip(),
        "requires_presence_traits": tuple(str(t).strip() for t in raw_event.get("requires_presence_traits", [])),
        "forbidden_presence_traits": tuple(str(t).strip() for t in raw_event.get("forbidden_presence_traits", [])),
        "required_flags": tuple(str(flag).strip() for flag in raw_event.get("required_flags", [])),
        "forbidden_flags": tuple(str(flag).strip() for flag in raw_event.get("forbidden_flags", [])),
        "tags": tuple(str(tag).strip() for tag in raw_event.get("tags", [])),
        "flavor": str(raw_event.get("flavor", "Something office-shaped happens.")).strip(),
        "effects": {
            "energy_delta": int(effects.get("energy_delta", 0)),
            "stress_delta": int(effects.get("stress_delta", 0)),
            "rep_delta": int(effects.get("rep_delta", 0)),
            "money_delta": int(effects.get("money_delta", 0)),
            "xp_delta": int(effects.get("xp_delta", 0)),
        },
    }
    return normalized


def event_is_eligible(
    raw_event: Mapping[str, Any],
    player_snapshot: Mapping[str, Any],
    active_flags: Iterable[str] = (),
) -> bool:
    event = normalize_event_template(raw_event)
    current_day = int(player_snapshot.get("day", 1))
    current_stress = int(player_snapshot.get("stress", 0))
    department = str(player_snapshot.get("department", "")).strip()
    presence_trait = str(player_snapshot.get("presence_trait", "")).strip()
    active_flag_set = {str(flag).strip() for flag in active_flags}

    if not event["id"]:
        return False
    if current_day < event["min_day"] or current_day > event["max_day"]:
        return False
    if current_stress < event["min_stress"] or current_stress > event["max_stress"]:
        return False
    if event["department"] and event["department"] != department:
        return False
    if event["requires_presence_traits"] and presence_trait not in event["requires_presence_traits"]:
        return False
    if presence_trait and presence_trait in event["forbidden_presence_traits"]:
        return False
    if any(flag not in active_flag_set for flag in event["required_flags"]):
        return False
    if any(flag in active_flag_set for flag in event["forbidden_flags"]):
        return False
    return True


def eligible_events(
    events: Iterable[Mapping[str, Any]],
    player_snapshot: Mapping[str, Any],
    active_flags: Iterable[str] = (),
) -> list[dict[str, Any]]:
    return [
        normalize_event_template(event)
        for event in events
        if event_is_eligible(event, player_snapshot, active_flags)
    ]


def pick_event(
    events: Iterable[Mapping[str, Any]],
    player_snapshot: Mapping[str, Any],
    active_flags: Iterable[str] = (),
    rng: random.Random | None = None,
) -> dict[str, Any] | None:
    candidates = eligible_events(events, player_snapshot, active_flags)
    if not candidates:
        return None

    chooser = rng or random
    weights = [max(1, int(event.get("weight", DEFAULT_WEIGHT))) for event in candidates]
    return chooser.choices(candidates, weights=weights, k=1)[0]


def resolve_event(raw_event: Mapping[str, Any]) -> dict[str, Any]:
    """
    Convert an event template into the standard engine result shape.
    """
    event = normalize_event_template(raw_event)
    result = empty_result()
    result["flavor"] = event["flavor"]
    result.update(event["effects"])
    return result

"""
result_contract.py — Standard shape for system-to-engine results.

Systems stay pure and return this dict shape. The engine owns mutation.
"""
from __future__ import annotations

from typing import Any, Mapping

OUTCOME_TIERS = {"dumpster_fire", "partial", "success", "legendary"}

RESULT_DEFAULTS: dict[str, Any] = {
    "outcome": "partial",
    "flavor": "",
    "energy_delta": 0,
    "stress_delta": 0,
    "rep_delta": 0,
    "money_delta": 0,
    "xp_delta": 0,
    "skill_deltas": {},
    "npc_deltas": {},
}


def empty_result(**overrides: Any) -> dict[str, Any]:
    result = dict(RESULT_DEFAULTS)
    result["skill_deltas"] = {}
    result["npc_deltas"] = {}
    result.update(overrides)
    if result["outcome"] not in OUTCOME_TIERS:
        result["outcome"] = "partial"
    return result


def normalize_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = empty_result()
    for key in RESULT_DEFAULTS:
        if key in payload:
            result[key] = payload[key]
    if result["outcome"] not in OUTCOME_TIERS:
        result["outcome"] = "partial"
    if not isinstance(result["skill_deltas"], dict):
        result["skill_deltas"] = {}
    if not isinstance(result["npc_deltas"], dict):
        result["npc_deltas"] = {}
    return result


def missing_result_keys(payload: Mapping[str, Any]) -> list[str]:
    return [key for key in RESULT_DEFAULTS if key not in payload]

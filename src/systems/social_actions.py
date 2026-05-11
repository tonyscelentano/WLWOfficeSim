"""
social_actions.py — Thin registry for explicit coworker social verbs

Keeps social action lookup separate from the scoring/resolution logic so engine
integration later stays simple and the social_economy module does not become a
god file.
"""
from __future__ import annotations

from typing import Any, Mapping

from .social_config import SOCIAL_ACTIONS
from .social_economy import resolve_social_action, social_action_plan


def list_social_actions() -> list[str]:
    return sorted(SOCIAL_ACTIONS)


def is_social_action(action: str) -> bool:
    return action.strip() in SOCIAL_ACTIONS


def plan_social_action(
    action: str,
    npc: Mapping[str, Any],
    player_snapshot: Mapping[str, Any],
    faction_topology: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return social_action_plan(action, npc, player_snapshot, faction_topology)


def execute_social_action(
    action: str,
    npc: Mapping[str, Any],
    player_snapshot: Mapping[str, Any],
    faction_topology: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return resolve_social_action(action, npc, player_snapshot, faction_topology)

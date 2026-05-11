"""
adapter.py — Published call shape for systems-owned logic.

Call envelope:
{
  "system": "career" | "events" | "relationship_perks" | "social_actions",
  "action": str,
  "payload": dict,
  "player_snapshot": dict,
  "data": dict,
  "context": dict,
}

Response envelope:
{
  "ok": bool,
  "kind": "result" | "plan" | "summary" | "data" | "none" | "error",
  "result": Result dict | None,
  "data": dict,
  "error": str | None,
}

This module is an adapter contract, not an engine. It does not mutate state.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

from .career import apply_promotion, check_promotion_eligibility, handle_bus_event
from .events import eligible_events, pick_event, resolve_event
from .relationship_perks import npc_access_perks, summarize_relationship_perks
from .result_contract import normalize_result
from .social_actions import execute_social_action, list_social_actions, plan_social_action
from .social import resolve_interaction
from .tasks import resolve_task
from .watercooler import choose_watercooler_context, watercooler_context_for_npc

SYSTEMS = {"career", "events", "relationship_perks", "social_actions", "tasks", "social", "watercooler"}


def make_call(
    system: str,
    action: str,
    payload: Mapping[str, Any] | None = None,
    player_snapshot: Mapping[str, Any] | None = None,
    data: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "system": str(system).strip(),
        "action": str(action).strip(),
        "payload": dict(payload or {}),
        "player_snapshot": dict(player_snapshot or {}),
        "data": dict(data or {}),
        "context": dict(context or {}),
    }


def response(
    kind: str,
    result: Mapping[str, Any] | None = None,
    data: Mapping[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    normalized_result = normalize_result(result) if result is not None else None
    return {
        "ok": error is None,
        "kind": "error" if error else kind,
        "result": normalized_result,
        "data": dict(data or {}),
        "error": error,
    }


def list_supported_calls() -> dict[str, list[str]]:
    return {
        "career": ["apply_promotion", "check_promotion", "handle_bus_event"],
        "events": ["eligible_events", "pick_event", "resolve_event"],
        "relationship_perks": ["npc_access_perks", "summarize"],
        "social_actions": ["execute", "list", "plan"],
        "tasks": ["resolve"],
        "social": ["resolve_interaction"],
        "watercooler": ["choose_context", "context_for_npc"],
    }


def _factions(call: Mapping[str, Any]) -> Mapping[str, Any]:
    data = call.get("data", {})
    return data.get("factions", {}) if isinstance(data, Mapping) else {}


def _active_flags(call: Mapping[str, Any]) -> list[str]:
    context = call.get("context", {})
    if not isinstance(context, Mapping):
        return []
    flags = context.get("active_flags", [])
    return list(flags) if isinstance(flags, list) else []


def _dispatch_career(call: Mapping[str, Any]) -> dict[str, Any]:
    action = call["action"]
    payload = call["payload"]
    player_snapshot = call["player_snapshot"]
    if action == "check_promotion":
        return response("data", data=check_promotion_eligibility(player_snapshot))
    if action == "apply_promotion":
        return response("result", result=apply_promotion(player_snapshot))
    if action == "handle_bus_event":
        result = handle_bus_event(
            str(payload.get("event_name", "")),
            payload.get("event_data", {}),
            player_snapshot,
        )
        return response("result", result=result) if result else response("none")
    return response("error", error=f"Unsupported career action: {action}")


def _dispatch_events(call: Mapping[str, Any]) -> dict[str, Any]:
    action = call["action"]
    payload = call["payload"]
    player_snapshot = call["player_snapshot"]
    events = payload.get("events", [])
    if action == "eligible_events":
        return response(
            "data",
            data={"events": eligible_events(events, player_snapshot, _active_flags(call))},
        )
    if action == "pick_event":
        event = pick_event(events, player_snapshot, _active_flags(call))
        return response("data", data={"event": event} if event else {})
    if action == "resolve_event":
        return response("result", result=resolve_event(payload.get("event", {})))
    return response("error", error=f"Unsupported events action: {action}")


def _dispatch_relationship_perks(call: Mapping[str, Any]) -> dict[str, Any]:
    action = call["action"]
    payload = call["payload"]
    player_snapshot = call["player_snapshot"]
    if action == "npc_access_perks":
        return response("data", data=npc_access_perks(payload.get("npc", {}), player_snapshot))
    if action == "summarize":
        return response("summary", data=summarize_relationship_perks(payload.get("npcs", []), player_snapshot))
    return response("error", error=f"Unsupported relationship_perks action: {action}")


def _dispatch_social_actions(call: Mapping[str, Any]) -> dict[str, Any]:
    action = call["action"]
    payload = call["payload"]
    player_snapshot = call["player_snapshot"]
    if action == "list":
        return response("data", data={"actions": list_social_actions()})
    if action == "plan":
        plan = plan_social_action(
            str(payload.get("social_action", "")),
            payload.get("npc", {}),
            player_snapshot,
            _factions(call),
        )
        return response("plan", data=plan)
    if action == "execute":
        result = execute_social_action(
            str(payload.get("social_action", "")),
            payload.get("npc", {}),
            player_snapshot,
            _factions(call),
        )
        return response("result", result=result)
    return response("error", error=f"Unsupported social_actions action: {action}")


def _dispatch_tasks(call: Mapping[str, Any]) -> dict[str, Any]:
    action = call["action"]
    payload = call["payload"]
    if action == "resolve":
        result = resolve_task(
            payload.get("task", {}),
            payload.get("player_input", ""),
            payload.get("skill_level", 1)
        )
        return response("result", result=result)
    return response("error", error=f"Unsupported tasks action: {action}")


def _dispatch_social(call: Mapping[str, Any]) -> dict[str, Any]:
    action = call["action"]
    payload = call["payload"]
    player_snapshot = call["player_snapshot"]
    if action == "resolve_interaction":
        result = resolve_interaction(
            payload.get("npc", {}),
            payload.get("archetype", {}),
            payload.get("player_input", ""),
            player_snapshot,
        )
        return response("result", result=result)
    return response("error", error=f"Unsupported social action: {action}")


def _dispatch_watercooler(call: Mapping[str, Any]) -> dict[str, Any]:
    action = call["action"]
    payload = call["payload"]
    if action == "choose_context":
        data = choose_watercooler_context(
            requested_npc_id=payload.get("requested_npc_id"),
            npcs=payload.get("npcs", {}),
            stress=payload.get("stress", 0),
            player_input=payload.get("player_input", ""),
            discovered_npcs=set(payload.get("discovered_npcs", [])),
            lock_requested_npc=bool(payload.get("lock_requested_npc", False)),
        )
        return response("data", data=data)
    if action == "context_for_npc":
        data = watercooler_context_for_npc(
            payload.get("npc_id", ""),
            payload.get("npcs", {}),
            payload.get("last_outcome", "partial"),
            payload.get("player_input", ""),
        )
        return response("data", data=data)
    return response("error", error=f"Unsupported watercooler action: {action}")


DISPATCHERS: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "career": _dispatch_career,
    "events": _dispatch_events,
    "relationship_perks": _dispatch_relationship_perks,
    "social_actions": _dispatch_social_actions,
    "tasks": _dispatch_tasks,
    "social": _dispatch_social,
    "watercooler": _dispatch_watercooler,
}


def dispatch(call: Mapping[str, Any]) -> dict[str, Any]:
    normalized = make_call(
        system=str(call.get("system", "")),
        action=str(call.get("action", "")),
        payload=call.get("payload", {}),
        player_snapshot=call.get("player_snapshot", {}),
        data=call.get("data", {}),
        context=call.get("context", {}),
    )
    dispatcher = DISPATCHERS.get(normalized["system"])
    if dispatcher is None:
        return response("error", error=f"Unsupported system: {normalized['system']}")
    return dispatcher(normalized)

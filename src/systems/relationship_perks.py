"""
relationship_perks.py — Lightweight relationship-derived access signals.

This module does not mutate state. It derives unlocks and sponsorship signals
from current relationships so future features can consume a stable summary.
"""
from __future__ import annotations

from typing import Any, Mapping

from .social_config import TRUST_TIERS


NPC_MECHANICAL_BENEFITS: dict[str, dict[str, list[str]]] = {
    "jason_it": {
        "warm": ["it_context_hints_stub"],
        "ally": ["engineering_task_assist_stub"],
        "sponsor": ["cto_access_support_stub"],
    },
}


def relationship_tier(trust: int, rivalry: int) -> str:
    if rivalry >= 60:
        return "rival"
    if trust >= TRUST_TIERS["sponsor"] and rivalry <= 20:
        return "sponsor"
    if trust >= TRUST_TIERS["ally"] and rivalry <= 35:
        return "ally"
    if trust >= TRUST_TIERS["warm"]:
        return "warm"
    if trust >= TRUST_TIERS["known"]:
        return "known"
    return "cold"


def relationship_for(player_snapshot: Mapping[str, Any], npc_id: str) -> Mapping[str, Any]:
    relationships = player_snapshot.get("relationships", {})
    if not isinstance(relationships, Mapping):
        return {}
    payload = relationships.get(npc_id, {})
    return payload if isinstance(payload, Mapping) else {}


def npc_access_perks(npc: Mapping[str, Any], player_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    npc_id = str(npc.get("id", "")).strip()
    rel = relationship_for(player_snapshot, npc_id)
    trust = int(rel.get("trust", npc.get("base_trust", 0)))
    rivalry = int(rel.get("rivalry", npc.get("base_rivalry", 0)))
    tier = relationship_tier(trust, rivalry)
    access_tags = list(npc.get("access_tags", []))
    influence_weight = int(npc.get("influence_weight", 0))

    unlocked_access: list[str] = []
    if tier in {"ally", "sponsor"}:
        unlocked_access = access_tags
    elif tier == "warm":
        unlocked_access = access_tags[:1]

    mechanical_benefits = list(NPC_MECHANICAL_BENEFITS.get(npc_id, {}).get(tier, []))

    return {
        "npc_id": npc_id,
        "tier": tier,
        "social_currency": str(npc.get("social_currency", "general_access")),
        "unlocked_access": unlocked_access,
        "mechanical_benefits": mechanical_benefits,
        "sponsorship": tier == "sponsor" and influence_weight >= 6,
        "rivalry_risk": tier == "rival",
        "influence_weight": influence_weight,
    }


def summarize_relationship_perks(
    npcs: list[Mapping[str, Any]],
    player_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    entries = [npc_access_perks(npc, player_snapshot) for npc in npcs]
    unlocked_access = sorted({tag for entry in entries for tag in entry["unlocked_access"]})
    mechanical_benefits = sorted({tag for entry in entries for tag in entry["mechanical_benefits"]})
    sponsors = [entry["npc_id"] for entry in entries if entry["sponsorship"]]
    rivalries = [entry["npc_id"] for entry in entries if entry["rivalry_risk"]]
    currencies = {
        entry["npc_id"]: entry["social_currency"]
        for entry in entries
        if entry["tier"] in {"warm", "ally", "sponsor"}
    }
    return {
        "unlocked_access": unlocked_access,
        "mechanical_benefits": mechanical_benefits,
        "sponsors": sponsors,
        "rivalries": rivalries,
        "active_currencies": currencies,
        "entries": entries,
    }

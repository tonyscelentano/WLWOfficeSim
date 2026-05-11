"""
social_economy.py — Org-topology-aware coworker socialization helpers

Pure logic that scores NPC relationship opportunities against the current player
state and the faction topology. This scaffolds the "social economy" without
touching UI or engine orchestration.
"""
from __future__ import annotations

from typing import Any, Mapping

from .social_config import (
    ARCHETYPE_PRIORITIES,
    CLUSTER_ADJACENCY,
    PRESENCE_STYLE_MODIFIERS,
    SOCIAL_ACTION_COSTS,
)
from .result_contract import empty_result


def _player_org_position(player_snapshot: Mapping[str, Any]) -> tuple[str, str, str]:
    department = str(player_snapshot.get("department", "")).strip()
    parts = department.split(".")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return "", "", ""


def _relationship_for_npc(player_snapshot: Mapping[str, Any], npc_id: str) -> Mapping[str, Any]:
    relationships = player_snapshot.get("relationships", {})
    if isinstance(relationships, Mapping):
        payload = relationships.get(npc_id, {})
        if isinstance(payload, Mapping):
            return payload
    return {}


def cluster_distance(player_cluster: str, npc_cluster: str) -> int:
    if not player_cluster or not npc_cluster:
        return 3
    if player_cluster == npc_cluster:
        return 0
    if npc_cluster in CLUSTER_ADJACENCY.get(player_cluster, set()):
        return 1
    if player_cluster in CLUSTER_ADJACENCY.get(npc_cluster, set()):
        return 1
    return 2


def social_opportunity_score(
    npc: Mapping[str, Any],
    player_snapshot: Mapping[str, Any],
    faction_topology: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Score an NPC as a relationship target.
    Returns a structured explanation so UI or orchestration can present why the
    character matters in the current social economy.
    """
    player_pillar, _, player_cluster = _player_org_position(player_snapshot)
    npc_cluster = str(npc.get("cluster", "")).strip()
    npc_pillar = str(npc.get("pillar", "")).strip()
    npc_id = str(npc.get("id", "")).strip()
    relationship = _relationship_for_npc(player_snapshot, npc_id)
    trust = int(relationship.get("trust", npc.get("base_trust", 0)))
    rivalry = int(relationship.get("rivalry", npc.get("base_rivalry", 0)))
    influence_weight = int(npc.get("influence_weight", 0))
    ambition = int(npc.get("ambition", 0))
    archetype = str(npc.get("archetype", "")).strip()
    social_currency, archetype_bias = ARCHETYPE_PRIORITIES.get(archetype, ("general_access", 3))
    distance = cluster_distance(player_cluster, npc_cluster)
    presence_trait = str(player_snapshot.get("presence_trait", "")).strip()
    presence_bias = PRESENCE_STYLE_MODIFIERS.get(presence_trait, {}).get(archetype, 0)

    score = 10
    score += influence_weight * 2
    score += archetype_bias
    score += max(0, 12 - abs(trust - 55))
    score -= rivalry
    score += max(0, 6 - distance * 3)
    score += presence_bias
    if npc_pillar and npc_pillar != player_pillar:
        score += 3
    if ambition >= 7:
        score += 2

    reasons: list[str] = []
    if distance == 0:
        reasons.append("same_cluster_access")
    elif distance == 1:
        reasons.append("adjacent_cluster_access")
    else:
        reasons.append("cross_org_bridge")
    if npc_pillar and npc_pillar != player_pillar:
        reasons.append("cross_pillar_visibility")
    if influence_weight >= 7:
        reasons.append("high_influence")
    if rivalry >= 20:
        reasons.append("rivalry_risk")
    if trust >= 60:
        reasons.append("relationship_momentum")
    if ambition >= 7:
        reasons.append("ambitious_gatekeeper")
    if faction_topology and npc_pillar in faction_topology.get("pillars", {}):
        reasons.append("mapped_to_org_topology")

    return {
        "npc_id": npc_id,
        "score": score,
        "social_currency": str(npc.get("social_currency", social_currency)),
        "cluster_distance": distance,
        "reasons": reasons,
        "access_tags": list(npc.get("access_tags", [])),
        "pillar": npc_pillar,
        "cluster": npc_cluster,
        "archetype": archetype,
    }


def social_action_plan(
    action: str,
    npc: Mapping[str, Any],
    player_snapshot: Mapping[str, Any],
    faction_topology: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Scaffold explicit social verbs into a normalized planner payload.
    The plan can be consumed by UI or orchestration later.
    """
    score = social_opportunity_score(npc, player_snapshot, faction_topology)
    action_key = str(action).strip()
    config = SOCIAL_ACTION_COSTS.get(action_key, {"energy": 5, "risk": 2})
    recommended = score["score"] >= 30
    if action_key == "gather_rumor" and "rivalry_risk" in score["reasons"]:
        recommended = False
    if action_key == "ask_for_favor" and score["cluster_distance"] > 1:
        recommended = False

    return {
        "action": action_key,
        "npc_id": score["npc_id"],
        "recommended": recommended,
        "estimated_energy_cost": config["energy"],
        "estimated_risk": config["risk"],
        "social_currency": score["social_currency"],
        "reasons": score["reasons"],
        "access_tags": score["access_tags"],
        "target_score": score["score"],
    }


def resolve_social_action(
    action: str,
    npc: Mapping[str, Any],
    player_snapshot: Mapping[str, Any],
    faction_topology: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Deterministic fallback-style resolution for explicit social verbs.
    This is separate from `social.py` so engine integration can happen later.
    """
    plan = social_action_plan(action, npc, player_snapshot, faction_topology)
    result = empty_result()
    result["energy_delta"] = -int(plan["estimated_energy_cost"])
    npc_id = str(npc.get("id", "")).strip()
    result["npc_deltas"] = {npc_id: {"trust": 0, "rivalry": 0}}
    action_key = plan["action"]
    score = int(plan["target_score"])

    if action_key == "seek_mentorship":
        if score >= 32:
            result["outcome"] = "success"
            result["xp_delta"] = 12
            result["npc_deltas"][npc_id] = {"trust": 6, "rivalry": -1}
            result["flavor"] = f"{npc.get('name', 'Your coworker')} gives you advice that is specific, useful, and mildly better than therapy."
        else:
            result["outcome"] = "partial"
            result["xp_delta"] = 5
            result["npc_deltas"][npc_id] = {"trust": 2, "rivalry": 0}
            result["flavor"] = f"{npc.get('name', 'Your coworker')} gives you decent advice, though some of it arrives pre-generic."
        return result

    if action_key == "ask_for_favor":
        if score >= 35:
            result["outcome"] = "success"
            result["rep_delta"] = 3
            result["npc_deltas"][npc_id] = {"trust": 4, "rivalry": 0}
            result["flavor"] = f"{npc.get('name', 'Your coworker')} spends political or practical capital on your behalf."
        else:
            result["outcome"] = "partial"
            result["stress_delta"] = 4
            result["npc_deltas"][npc_id] = {"trust": -1, "rivalry": 1}
            result["flavor"] = f"The ask lands awkwardly. {npc.get('name', 'Your coworker')} does not say no, which is almost worse."
        return result

    if action_key == "gather_rumor":
        if score >= 28:
            result["outcome"] = "success"
            result["rep_delta"] = 1
            result["npc_deltas"][npc_id] = {"trust": 1, "rivalry": 0}
            result["flavor"] = f"You learn something useful about the office weather without becoming the weather."
        else:
            result["outcome"] = "dumpster_fire"
            result["stress_delta"] = 6
            result["npc_deltas"][npc_id] = {"trust": -3, "rivalry": 2}
            result["flavor"] = f"You go fishing for gossip and somehow become part of the story."
        return result

    if action_key == "relationship_maintenance":
        result["outcome"] = "success"
        result["npc_deltas"][npc_id] = {"trust": 3, "rivalry": -1}
        result["flavor"] = f"You keep the relationship warm with the office equivalent of watering a plant before it files a ticket."
        return result

    if score >= 26:
        result["outcome"] = "success"
        result["npc_deltas"][npc_id] = {"trust": 2, "rivalry": 0}
        result["flavor"] = f"The conversation lands cleanly. {npc.get('name', 'Your coworker')} leaves with a better impression than they started with."
    else:
        result["outcome"] = "partial"
        result["stress_delta"] = 2
        result["npc_deltas"][npc_id] = {"trust": 1, "rivalry": 0}
        result["flavor"] = f"The interaction is serviceable. Nobody wins a statue, but nobody schedules a damage-control meeting either."
    return result


def rank_social_targets(
    npcs: list[Mapping[str, Any]],
    player_snapshot: Mapping[str, Any],
    faction_topology: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    ranked = [
        social_opportunity_score(npc, player_snapshot, faction_topology)
        for npc in npcs
    ]
    ranked.sort(key=lambda item: (-int(item["score"]), item["npc_id"]))
    return ranked


def summarize_cluster_map(faction_topology: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Flatten the org topology into cluster metadata useful for routing and UI.
    """
    summary: dict[str, dict[str, Any]] = {}
    pillars = faction_topology.get("pillars", {})
    if not isinstance(pillars, Mapping):
        return summary

    for pillar_id, pillar_data in pillars.items():
        if not isinstance(pillar_data, Mapping):
            continue
        paths = pillar_data.get("paths", {})
        if not isinstance(paths, Mapping):
            continue
        for path_id, path_data in paths.items():
            if not isinstance(path_data, Mapping):
                continue
            clusters = path_data.get("clusters", {})
            if not isinstance(clusters, Mapping):
                continue
            for cluster_id, cluster_data in clusters.items():
                if not isinstance(cluster_data, Mapping):
                    continue
                summary[str(cluster_id)] = {
                    "pillar": str(pillar_id),
                    "path": str(path_id),
                    "name": str(cluster_data.get("name", cluster_id)),
                    "roles": list(cluster_data.get("roles", [])),
                    "adjacent_clusters": sorted(CLUSTER_ADJACENCY.get(str(cluster_id), set())),
                }
    return summary

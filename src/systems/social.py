import json
import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

from core.llm import call_llm_json, is_available as llm_available
from core.voice import social_evaluation_prompt
from .social_economy import cluster_distance

OUTCOME_TIERS = ["dumpster_fire", "partial", "success", "legendary"]

def evaluate_interaction(
    npc: Dict[str, Any], 
    archetype: Dict[str, Any], 
    player_input: str, 
    player_snapshot: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates a social interaction with an NPC using the NIM LLM backend, with a fallback to stat checks.
    
    Args:
        npc: The NPC definition dictionary (from npcs.toml).
        archetype: The archetype definition dictionary (from interactions.toml).
        player_input: The string input provided by the player.
        player_snapshot: Dictionary containing current player stats (skills, rep, etc.).
        
    Returns:
        A Result dict containing the outcome, flavor text, and stat/relationship deltas.
    """
    result = {
        "outcome": "partial",
        "flavor": "",
        "energy_delta": -5, # Base energy cost for socializing
        "stress_delta": 0,
        "rep_delta": 0,
        "money_delta": 0,
        "xp_delta": 0,
        "skill_deltas": {},
        "npc_deltas": {
            npc["id"]: {"trust": 0, "rivalry": 0}
        }
    }
    
    if llm_available():
        system_prompt = social_evaluation_prompt(
            npc=npc,
            archetype=archetype,
            player_snapshot=player_snapshot,
            player_input=player_input,
        )
        user_prompt = f"Player says/does: {player_input}"
        
        log.debug(f"evaluate_interaction sending prompt:\n{user_prompt}")

        llm_result = call_llm_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=1,
            max_tokens=4096,
        )
        
        if llm_result is not None:
            result["outcome"] = llm_result.get("outcome", "partial")
            if result["outcome"] not in OUTCOME_TIERS:
                result["outcome"] = "partial"
                
            result["flavor"] = llm_result.get("flavor", f"{npc.get('name')} nods.")
            result["energy_delta"] = int(llm_result.get("energy_delta", result["energy_delta"]))
            result["stress_delta"] = int(llm_result.get("stress_delta", 0))
            result["rep_delta"] = int(llm_result.get("rep_delta", 0))
            
            trust = int(llm_result.get("trust_delta", 0))
            rivalry = int(llm_result.get("rivalry_delta", 0))
            result["npc_deltas"][npc["id"]] = {"trust": trust, "rivalry": rivalry}
            
            if llm_result.get("scene_override"):
                result["scene_override"] = llm_result.get("scene_override")
        else:
            result = _stat_check_fallback(npc, archetype, player_snapshot, result)
            result["flavor"] = f"[LLM Error - Fallback] {result['flavor']}"
    else:
        log.warning("LLM not available. Using fallback interaction.")
        result = _stat_check_fallback(npc, archetype, player_snapshot, result)

    # Communication Skill XP gain based on interaction tier
    if result["outcome"] in ["success", "legendary"]:
        result["xp_delta"] += 10
    elif result["outcome"] == "partial":
        result["xp_delta"] += 5

    return result

def _stat_check_fallback(
    npc: Dict[str, Any], 
    archetype: Dict[str, Any], 
    player_snapshot: Dict[str, Any], 
    result_template: Dict[str, Any]
) -> Dict[str, Any]:
    """Fallback logic utilizing communication skill plus social-economy context."""
    comm_skill = player_snapshot.get("skills", {}).get("communication", 0)
    player_department = str(player_snapshot.get("department", "")).strip()
    player_cluster = player_department.split(".")[-1] if "." in player_department else ""
    npc_cluster = str(npc.get("cluster", "")).strip()
    archetype_id = str(archetype.get("id", npc.get("archetype", ""))).strip()
    distance = cluster_distance(player_cluster, npc_cluster)
    ambition = int(npc.get("ambition", 5))
    influence_weight = int(npc.get("influence_weight", 0))
    trust = int(
        player_snapshot.get("relationships", {}).get(npc.get("id", ""), {}).get(
            "trust",
            npc.get("base_trust", 0),
        )
    )
    dc = ambition + distance
    if influence_weight >= 7:
        dc += 1
    if trust >= 60:
        dc -= 1
    if archetype_id == "mentor":
        dc -= 1
    elif archetype_id == "political":
        dc += 1
    dc = max(2, dc)

    if comm_skill >= dc + 2:
        outcome = "success"
        if distance == 0:
            flavor = f"{npc.get('name')} clocks that you understand their world and responds with actual warmth."
        else:
            flavor = f"{npc.get('name')} seems genuinely impressed that you navigated the cross-functional gap without embarrassing anyone."
        trust_d = 10 if archetype_id != "gossip" else 6
        riv_d = -2
        result_template["rep_delta"] = 2 if influence_weight >= 7 else 0
    elif comm_skill >= dc - 1:
        outcome = "partial"
        flavor = f"{npc.get('name')} gives you a polite nod. The interaction survives contact with the office."
        trust_d = 2 if trust < 70 else 1
        riv_d = 0
        result_template["stress_delta"] = 1 if distance > 1 else 0
    else:
        outcome = "dumpster_fire"
        if archetype_id == "gossip":
            flavor = f"You misread the rumor economy completely. {npc.get('name')} now has content."
        elif archetype_id == "operator":
            flavor = f"You add chaos to an already fragile process. {npc.get('name')} looks tired in a deeply administrative way."
        else:
            flavor = f"You completely misread the room. {npc.get('name')} looks annoyed."
        trust_d = -10 if distance <= 1 else -6
        riv_d = 5 if influence_weight >= 6 else 3
        result_template["stress_delta"] = 15 if distance <= 1 else 10

    result_template["outcome"] = outcome
    result_template["flavor"] = flavor
    result_template["npc_deltas"][npc["id"]] = {"trust": trust_d, "rivalry": riv_d}
    
    return result_template


def resolve_interaction(
    npc: Dict[str, Any],
    archetype: Dict[str, Any],
    player_input: str,
    player_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """Engine-facing compatibility wrapper."""
    return evaluate_interaction(npc, archetype, player_input, player_snapshot)

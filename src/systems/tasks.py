import os
import json
import random
import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

from core.llm import call_llm_json, is_available as llm_available
from core.voice import task_evaluation_prompt

OUTCOME_TIERS = ["dumpster_fire", "partial", "success", "legendary"]

def evaluate_task(task: Dict[str, Any], player_input: str, skill_level: int) -> Dict[str, Any]:
    """
    Evaluates a task attempt using the NIM LLM backend, with a fallback to stat checks.
    
    Args:
        task: The task definition dictionary (from tasks.toml).
        player_input: The string input provided by the player describing their action.
        skill_level: The player's current integer level in the task's required_skill.
        
    Returns:
        A Result dict containing the outcome, flavor text, and stat deltas.
    """
    # Base structure of the result dictionary
    result = {
        "outcome": "partial",
        "flavor": "",
        "energy_delta": -task.get("energy_cost", 10),
        "stress_delta": 0,
        "rep_delta": 0,
        "money_delta": 0,
        "xp_delta": 0,
        "skill_deltas": {},
        "npc_deltas": {}
    }
    
    if llm_available():
        system_prompt = task_evaluation_prompt(task, skill_level)
        user_prompt = f"Player action: {player_input}"

        log.debug(f"evaluate_task sending prompt:\n{user_prompt}")

        llm_result = call_llm_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=1,
            max_tokens=4096,
        )
        
        if llm_result is not None:
            # Map LLM results to the result dict safely
            result["outcome"] = llm_result.get("outcome", "partial")
            if result["outcome"] not in OUTCOME_TIERS:
                result["outcome"] = "partial"
                
            result["flavor"] = llm_result.get("flavor", "You completed the task.")
            result["energy_delta"] = int(llm_result.get("energy_delta", result["energy_delta"]))
            result["stress_delta"] = int(llm_result.get("stress_delta", 0))
            result["rep_delta"] = int(llm_result.get("rep_delta", 0))
            result["money_delta"] = int(llm_result.get("money_delta", 0))
            result["xp_delta"] = int(llm_result.get("xp_delta", 0))
        else:
            # LLM returned None — JSON parse or network failure
            result = _stat_check_fallback(task, skill_level, result)
            result["flavor"] = f"[LLM Error - Fallback] {result['flavor']}"
    else:
        log.warning("LLM not available. Using fallback task evaluation.")
        result = _stat_check_fallback(task, skill_level, result)
        
    # Legendary Perk: Probabilistic (40% chance) skill point gain
    if result["outcome"] == "legendary":
        if random.random() < 0.40:
            req_skill = task.get("required_skill")
            if req_skill:
                result["skill_deltas"][req_skill] = 1
                result["flavor"] += f" You gained a permanent point in {req_skill}!"

    return result

def _stat_check_fallback(task: Dict[str, Any], skill_level: int, result_template: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback logic utilizing the fallback_dc stat check."""
    dc = task.get("fallback_dc", 5)
    
    if skill_level >= dc + 3:
        if random.random() < 0.10: # Small chance of natural legendary
            outcome = "legendary"
            flavor = "You absolutely crushed it with mechanical precision."
        else:
            outcome = "success"
            flavor = "You completed the task smoothly."
    elif skill_level >= dc:
        outcome = "success"
        flavor = "You managed to get it done."
    elif skill_level < dc - 2:
        outcome = "dumpster_fire"
        flavor = "It was a complete disaster. You broke everything."
    else:
        outcome = "partial"
        flavor = "You made some progress, but it's not quite right."
        
    result_template["outcome"] = outcome
    result_template["flavor"] = flavor
    
    # Simple stat impacts based on outcome
    if outcome in ["success", "legendary"]:
        result_template["rep_delta"] = task.get("reward_rep", 10)
        result_template["xp_delta"] = 20
        result_template["stress_delta"] = -5
    elif outcome == "partial":
        result_template["rep_delta"] = task.get("reward_rep", 10) // 2
        result_template["xp_delta"] = 10
        result_template["stress_delta"] = task.get("risk_stress", 15) // 2
    else: # dumpster_fire
        result_template["rep_delta"] = -10
        result_template["xp_delta"] = 5
        result_template["stress_delta"] = task.get("risk_stress", 15)

    return result_template


def resolve_task(task: Any, player_input: str, skill_level: int) -> Dict[str, Any]:
    """
    Engine-facing compatibility wrapper.
    Accepts either a TaskInstance (dataclass) or a plain dict task payload.
    """
    if hasattr(task, "to_dict"):
        task_payload = task.to_dict()
    elif isinstance(task, dict):
        task_payload = task
    else:
        task_payload = dict(task)
    return evaluate_task(task_payload, player_input, skill_level)

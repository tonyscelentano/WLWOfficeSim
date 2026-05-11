import json
import logging
from typing import Dict, Any, List

log = logging.getLogger(__name__)

from core.llm import call_llm, call_llm_json, is_available as llm_available
from core.voice import (
    interview_evaluation_prompt,
    interview_followup_prompt,
    interview_opening_prompt,
    interview_opening_question,
)

def _application_fallback_question(application_context: Dict[str, Any] | None = None) -> str:
    application_context = application_context or {}
    name = str(application_context.get("name", "")).strip() or "candidate"
    preferred = str(application_context.get("preferred_role", "")).strip()
    history = str(application_context.get("work_history", "")).strip()
    if preferred:
        return f"Welcome, {name}. Your form says '{preferred}', which is either a career goal or a warning label; when the office starts wobbling, do you sell the vision, fix the system, or turn it into a meeting?"
    if history:
        short_history = history[:90].rstrip()
        return f"Welcome, {name}. Your work history mentions '{short_history}', which HR has placed gently in the evidence pile; what kind of office disaster do you usually become useful during?"
    return interview_opening_question()


def get_initial_question(application_context: Dict[str, Any] | None = None) -> str:
    """Returns the starting question for the interview."""
    log.info(f"LLM Onboarding Check: available={llm_available()}")
    
    if not application_context:
        return interview_opening_question()
    if not llm_available():
        log.warning("LLM not available. Using contextual fallback opening.")
        return _application_fallback_question(application_context)

    question = call_llm(
        system_prompt=interview_opening_prompt(application_context),
        temperature=0.8,
        max_tokens=512,
    )
    return question or _application_fallback_question(application_context)


def get_next_question(
    transcript: List[Dict[str, str]],
    application_context: Dict[str, Any] | None = None,
) -> str:
    """Generates a dynamic follow-up question based on the interview transcript."""
    if not llm_available():
        log.warning("LLM not available. Using fallback question.")
        preferred = str((application_context or {}).get("preferred_role", "")).strip()
        if preferred:
            return f"Interesting. Since you wrote down '{preferred}', what would you do when that job is suddenly 40% stakeholder theater and 60% spreadsheet weather?"
        return "Interesting. When the office is one bad dashboard away from chaos, do you fix the thing, smooth the room, or quietly invent a better process?"
        
    messages = [{"role": "system", "content": interview_followup_prompt(transcript, application_context)}]
    for turn in transcript:
        role = "assistant" if turn["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": turn["content"]})

    result = call_llm(
        system_prompt="",  # already in messages
        messages=messages,
        temperature=0.8,
        max_tokens=1024,
    )
    return result or "I see. And how do you handle conflict with difficult coworkers?"


def evaluate_interview(
    transcript: List[Dict[str, str]],
    application_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Evaluates the entire interview transcript to sort the player and assign starting stats."""
    result = {
        "pillar": "technical",
        "path": "middle",
        "cluster": "backend",
        "role": "Junior Backend Dev",
        "starting_skills": {
            "engineering": 5, "communication": 2, "sales": 0, "leadership": 1, "creativity": 3
        },
        "flavor": "The interview was inconclusive, so we stuck you in the backend mines."
    }
    
    if not llm_available():
        log.warning("LLM not available. Using fallback sort.")
        return result
        
    try:
        transcript_text = "\n".join([f"{t['role'].capitalize()}: {t['content']}" for t in transcript])
        user_prompt = f"Interview Transcript:\n{transcript_text}"

        llm_result = call_llm_json(
            system_prompt=interview_evaluation_prompt(transcript, application_context),
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=4096,
        )
        
        if llm_result is None:
            result["flavor"] = f"[LLM Error - Assigned Default] {result['flavor']}"
            return result
        
        # Validation and Mapping
        from core.loader import load_factions
        factions = load_factions()
        valid_pillars = factions.get("pillars", {})
        
        # Pillar validation
        pillar = llm_result.get("pillar", "technical")
        if pillar not in valid_pillars:
            pillar = "technical"
        result["pillar"] = pillar
        
        # Path and Cluster validation
        path = llm_result.get("path", "middle")
        valid_paths = valid_pillars.get(pillar, {}).get("paths", {})
        if path not in valid_paths:
            # Pick first available path if LLM is wrong
            path = next(iter(valid_paths.keys())) if valid_paths else "middle"
        result["path"] = path
        
        cluster = llm_result.get("cluster", "backend")
        valid_clusters = valid_paths.get(path, {}).get("clusters", {})
        if cluster not in valid_clusters:
            cluster = next(iter(valid_clusters.keys())) if valid_clusters else "backend"
        result["cluster"] = cluster
        
        result["role"] = llm_result.get("role", result["role"])
        result["flavor"] = llm_result.get("flavor", result["flavor"])
        
        skills = llm_result.get("starting_skills", {})
        for k in result["starting_skills"].keys():
            result["starting_skills"][k] = int(skills.get(k, result["starting_skills"][k]))
            
    except Exception as e:
        log.exception("LLM Error or JSON Parsing Error in evaluate_interview")
        result["flavor"] = f"[LLM Error - Assigned Default] {result['flavor']}"

    return result

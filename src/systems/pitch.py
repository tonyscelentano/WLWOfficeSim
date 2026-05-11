import json
import random
import logging
from typing import Dict, Any
from core.voice import pitch_evaluation_prompt
from core.llm import call_llm_json, is_available as llm_available

log = logging.getLogger(__name__)


def evaluate_pitch(deck_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls the LLM to evaluate a satirical pitch deck.
    Falls back to a randomized response if no LLM is configured.
    """
    if not llm_available():
        log.warning("LLM not configured for Pitch Evaluation. Falling back to local logic.")
        return _pitch_fallback(deck_data)

    prompt = pitch_evaluation_prompt(deck_data)
    
    result = call_llm_json(
        system_prompt=prompt,
        model="nvidia/llama-3.1-8b-instruct",
        temperature=0.7,
        max_tokens=256,
        stream=False,
    )
    
    if result is not None:
        return result
    
    log.error("Pitch LLM evaluation failed — using fallback.")
    return _pitch_fallback(deck_data)


def _pitch_fallback(deck: Dict[str, Any]) -> Dict[str, Any]:
    outcomes = [
        { "outcome": "success", "flavor": f"The board at {deck.get('company')} stood in silent awe. They requested three follow-up meetings to discuss 'synergy optimization'.", "energy_delta": -15, "stress_delta": -10 },
        { "outcome": "partial", "flavor": f"Eyebrows were quizzical as you explained the '{deck.get('verb')}' strategy. They're intrigued but concerned about the {deck.get('font')} font.", "energy_delta": -20, "stress_delta": 5 },
        { "outcome": "failure", "flavor": f"A single cough echoed through the boardroom. The CEO asked if this was a prank. The {deck.get('company')} vision is currently pending deletion.", "energy_delta": -25, "stress_delta": 20 }
    ]
    return random.choice(outcomes)

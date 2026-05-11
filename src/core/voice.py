from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import tomllib

DATA_DIR = Path(__file__).parent.parent / "data"
VOICE_FILE = DATA_DIR / "voices.toml"


@lru_cache(maxsize=1)
def _load_voice_pack() -> dict[str, Any]:
    if not VOICE_FILE.exists():
        return {}
    with VOICE_FILE.open("rb") as f:
        return tomllib.load(f)


def _section(name: str, fallback: str = "") -> str:
    pack = _load_voice_pack()
    return str(pack.get(name, {}).get("tone", fallback)).strip()


def _prompt_tmpl(name: str) -> str:
    pack = _load_voice_pack()
    return str(pack.get("prompts", {}).get(name, "")).strip()


def _format_transcript(transcript: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for turn in transcript:
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "").strip()
        lines.append(f"{role}: {content}")
    return "\n".join(lines).strip()


def _format_application_context(application_context: Mapping[str, Any] | None = None) -> str:
    if not application_context:
        return "No application form was provided. Treat the candidate as a fresh mystery with shoes."

    fields = {
        "Name": application_context.get("name", ""),
        "Age": application_context.get("age", ""),
        "Preferred office destiny": application_context.get("preferred_role", ""),
        "Work history, approximately": application_context.get("work_history", ""),
    }
    lines = [
        f"{label}: {str(value).strip()}"
        for label, value in fields.items()
        if str(value).strip()
    ]
    return "\n".join(lines) if lines else "The application exists but says almost nothing. HR considers this a bold minimalist statement."


def _match_entry(entries: list[dict[str, Any]], entry_id: str) -> dict[str, Any] | None:
    return next((entry for entry in entries if entry.get("id") == entry_id), None)


def _pick_template(value: Any, default: str) -> str:
    if isinstance(value, dict):
        return str(value.get("general", default)).strip() or default
    if isinstance(value, list):
        for item in value:
            if str(item).strip():
                return str(item).strip()
        return default
    if isinstance(value, str):
        return value.strip() or default
    return default


def office_tone() -> str:
    return _section(
        "global",
        "OfficeSim is workplace satire. Keep every response dry, playful, and lightly absurd.",
    )


def interview_opening_question() -> str:
    pack = _load_voice_pack()
    interview = pack.get("interview", {})
    return str(
        interview.get(
            "opening_question",
            "Welcome to OfficeSim. If this office were a small disaster with snacks, would you fix the thing, sell the thing, or turn the thing into a meeting?",
        )
    )


def interview_opening_prompt(application_context: Mapping[str, Any] | None = None) -> str:
    return _prompt_tmpl("interview_opening").format(
        tone=office_tone(),
        application=_format_application_context(application_context)
    )


def interview_followup_prompt(
    transcript: list[dict[str, str]],
    application_context: Mapping[str, Any] | None = None,
) -> str:
    return _prompt_tmpl("interview_followup").format(
        tone=office_tone(),
        application=_format_application_context(application_context),
        transcript=_format_transcript(transcript)
    )


def _format_factions() -> str:
    """Flatten factions.toml into a list of valid placement options for the LLM."""
    from .loader import load_factions
    try:
        factions = load_factions()
        lines: list[str] = []
        pillars = factions.get("pillars", {})
        for pillar_id, pillar_data in pillars.items():
            pillar_name = pillar_data.get("name", pillar_id)
            lines.append(f"Pillar: '{pillar_id}' ({pillar_name})")
            paths = pillar_data.get("paths", {})
            for path_id, path_data in paths.items():
                clusters = path_data.get("clusters", {})
                cluster_list = ", ".join(f"'{c}'" for c in clusters.keys())
                lines.append(f"  - Path '{path_id}': Clusters: {cluster_list}")
        return "\n".join(lines)
    except Exception:
        return "Standard Pillars: technical, fulfillment, finance. Paths: left, middle, right."


def interview_evaluation_prompt(
    transcript: list[dict[str, str]],
    application_context: Mapping[str, Any] | None = None,
) -> str:
    return _prompt_tmpl("interview_evaluation").format(
        tone=office_tone(),
        factions=_format_factions(),
        application=_format_application_context(application_context),
        transcript=_format_transcript(transcript)
    )


def task_evaluation_prompt(task: Mapping[str, Any], skill_level: int) -> str:
    return _prompt_tmpl("task_evaluation").format(
        tone=office_tone(),
        title=task.get('title', 'Unknown Task'),
        required_skill=task.get('required_skill', 'general'),
        skill_level=skill_level,
        hint=task.get('evaluation_hint', 'Evaluate the answer in a workplace-satire tone.')
    )


def _npc_persona_block(npc: Mapping[str, Any], archetype: Mapping[str, Any] | None) -> str:
    pack = _load_voice_pack()
    npc_entries = pack.get("npc_personas", [])
    archetype_entries = pack.get("archetype_personas", [])

    npc_entry = _match_entry(npc_entries, str(npc.get("id", ""))) or {}
    archetype_entry = {}
    if archetype:
        archetype_entry = _match_entry(archetype_entries, str(archetype.get("id", ""))) or {}

    pieces: list[str] = [
        f"NPC name: {npc.get('name', 'Coworker')}",
        f"Role: {npc.get('role', 'Employee')}",
        f"Description: {npc.get('description', 'A coworker in the office ecosystem.')}",
        f"Communication style: {npc.get('communication_style', 'professional')}",
    ]

    for entry in (npc_entry, archetype_entry):
        if entry.get("tone"):
            pieces.append(str(entry["tone"]).strip())
        if entry.get("examples"):
            examples = "\n".join(f"- {ex}" for ex in entry["examples"])
            pieces.append(f"Examples:\n{examples}")

    return "\n".join(piece for piece in pieces if piece).strip()


def social_evaluation_prompt(
    npc: Mapping[str, Any],
    archetype: Mapping[str, Any],
    player_snapshot: Mapping[str, Any],
    player_input: str,
) -> str:
    prompt_template = _pick_template(npc.get("prompt_templates"), "")
    if not prompt_template:
        prompt_template = _pick_template(archetype.get("templates"), "Respond to the player.")

    history_str = ""
    social_log = player_snapshot.get("social_log", [])
    if social_log:
        recent = social_log[-5:] # Keep it focused
        history_str = "\nRecent Conversation:\n" + "\n".join(
            f"{entry['name']}: {entry['text']}" for entry in recent
        )

    return _prompt_tmpl("social_evaluation").format(
        tone=office_tone(),
        npc_name=npc.get('name'),
        history=history_str,
        persona_block=_npc_persona_block(npc, archetype),
        scenario=prompt_template,
        input=player_input
    )


def pitch_evaluation_prompt(deck: Mapping[str, Any]) -> str:
    return _prompt_tmpl("pitch_evaluation").format(
        tone=office_tone(),
        company=deck.get('company'),
        font=deck.get('font'),
        verb=deck.get('verb'),
        noun=deck.get('noun'),
        adjective=deck.get('adjective'),
        theme=deck.get('theme')
    )


def gremlin_quest_prompt(
    stage: int,
    player_input: str,
    player_snapshot: Mapping[str, Any],
    objective: str | None = None,
    success_cues: list[str] | None = None,
    failure_cues: list[str] | None = None,
) -> str:
    mission = objective or {
        "1": "Protect the fiber cables from being eaten.",
        "2": "Stop the gremlins from using the 386 servers to mine crypto.",
        "3": "Evict the Gremlin Manager and send them to Marketing."
    }.get(str(stage), "Survive the chaos.")
    
    return _prompt_tmpl("gremlin_quest").format(
        tone=office_tone(),
        stage=stage,
        mission=mission,
        input=player_input,
        success_cues=", ".join(success_cues or []),
        failure_cues=", ".join(failure_cues or []),
    )

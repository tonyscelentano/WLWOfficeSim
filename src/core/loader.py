"""
loader.py — TOML Data Hydration

Owns reading and validating the data files.
Returns typed dicts that engine.py uses to seed the initial GameState.
Nothing here mutates state — pure input pipeline.

All TOML files are treated as immutable templates.
Runtime copies live in GameState; loader is only called at game start (or on new game).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import tomllib

log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"

NPC_FILE         = DATA_DIR / "npcs.toml"
TASK_FILE        = DATA_DIR / "tasks.toml"
INTERACTION_FILE = DATA_DIR / "interactions.toml"
FACTIONS_FILE    = DATA_DIR / "factions.toml"
STRINGS_FILE     = DATA_DIR / "strings.toml"


# ── Required fields (validation) ──────────────────────────────────────────────
_REQUIRED_NPC_FIELDS = {
    "id", "name", "role", "department", "reports_to",
    "archetype", "ambition", "base_trust", "base_rivalry",
    "influence_weight", "influence_scope", "communication_style",
    "pillar", "path", "cluster", "social_currency", "access_tags",
}

_REQUIRED_TASK_FIELDS = {
    "id", "title", "task_type", "energy_cost", "deadline_days",
    "reward_rep", "reward_money", "risk_stress", "required_skill",
    "fallback_dc", "prompt_template", "evaluation_hint",
}

_REQUIRED_ARCHETYPE_FIELDS = {"id", "outcome_hints", "templates"}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def _validate(records: list[dict], required: set[str], label: str) -> None:
    for i, record in enumerate(records):
        missing = required - record.keys()
        if missing:
            raise ValueError(
                f"{label}[{i}] (id={record.get('id', '?')!r}) "
                f"missing required fields: {sorted(missing)}"
            )


def _validate_npc_topology(npcs: list[dict[str, Any]]) -> None:
    valid_pillars = {"technical", "fulfillment", "finance"}
    valid_paths = {"left", "middle", "right"}
    for npc in npcs:
        npc_id = npc.get("id", "?")
        pillar = npc.get("pillar")
        path = npc.get("path")
        cluster = npc.get("cluster")
        access_tags = npc.get("access_tags")
        if pillar not in valid_pillars:
            raise ValueError(f"NPC {npc_id!r} has invalid pillar: {pillar!r}")
        if path not in valid_paths:
            raise ValueError(f"NPC {npc_id!r} has invalid path: {path!r}")
        if not isinstance(cluster, str) or not cluster.strip():
            raise ValueError(f"NPC {npc_id!r} missing usable cluster value.")
        if not isinstance(access_tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in access_tags):
            raise ValueError(f"NPC {npc_id!r} has invalid access_tags list.")


def _cluster_ids_from_factions(data: dict[str, Any]) -> set[str]:
    cluster_ids: set[str] = set()
    pillars = data.get("pillars", {})
    if not isinstance(pillars, dict):
        return cluster_ids
    for pillar_data in pillars.values():
        if not isinstance(pillar_data, dict):
            continue
        paths = pillar_data.get("paths", {})
        if not isinstance(paths, dict):
            continue
        for path_data in paths.values():
            if not isinstance(path_data, dict):
                continue
            clusters = path_data.get("clusters", {})
            if not isinstance(clusters, dict):
                continue
            cluster_ids.update(str(cluster_id) for cluster_id in clusters.keys())
    return cluster_ids


# ── Public API ────────────────────────────────────────────────────────────────

def load_npcs() -> list[dict[str, Any]]:
    """
    Load and validate all NPC templates.
    Returns raw dicts — engine seeds GameState relationships from base_trust / base_rivalry.
    """
    data = _load_toml(NPC_FILE)
    npcs: list[dict] = data.get("npcs", [])
    if not npcs:
        log.warning("npcs.toml loaded with zero NPC entries.")
    _validate(npcs, _REQUIRED_NPC_FIELDS, "NPC")
    _validate_npc_topology(npcs)
    log.info("Loaded %d NPC template(s).", len(npcs))
    return npcs


def load_tasks() -> list[dict[str, Any]]:
    """
    Load and validate all task templates.
    Returns raw dicts — engine instantiates TaskInstance objects from these.
    """
    data = _load_toml(TASK_FILE)
    tasks: list[dict] = data.get("tasks", [])
    if not tasks:
        log.warning("tasks.toml loaded with zero task entries.")
    _validate(tasks, _REQUIRED_TASK_FIELDS, "Task")
    log.info("Loaded %d task template(s).", len(tasks))
    return tasks


def load_interactions() -> dict[str, dict[str, Any]]:
    """
    Load archetype interaction templates.
    Returns a dict keyed by archetype id for O(1) lookup in social.py.
    Per-NPC overrides in npcs.toml take precedence — this is the fallback layer.
    """
    data = _load_toml(INTERACTION_FILE)
    archetypes: list[dict] = data.get("archetypes", [])
    if not archetypes:
        log.warning("interactions.toml loaded with zero archetype entries.")
    _validate(archetypes, _REQUIRED_ARCHETYPE_FIELDS, "Archetype")
    keyed = {a["id"]: a for a in archetypes}
    log.info("Loaded %d archetype template(s).", len(keyed))
    return keyed


def load_factions() -> dict[str, Any]:
    """
    Load the org topology used by social economy and career-routing systems.
    Returns the raw nested TOML structure keyed by crown / pillars.
    """
    data = _load_toml(FACTIONS_FILE)
    if not data:
        log.warning("factions.toml loaded with no topology data.")
    else:
        log.info(
            "Loaded faction topology: crown=%s, pillars=%d.",
            "crown" in data,
            len(data.get("pillars", {})),
        )
    return data


def load_strings() -> dict[str, Any]:
    """Load UI and system flavor strings from TOML."""
    try:
        return _load_toml(STRINGS_FILE)
    except Exception:
        log.exception("Failed to load strings.toml, using empty defaults.")
        return {}


def _validate_npc_clusters_against_factions(
    npcs: list[dict[str, Any]],
    factions: dict[str, Any],
) -> None:
    valid_clusters = _cluster_ids_from_factions(factions)
    if not valid_clusters:
        raise ValueError("Faction topology contains no cluster ids to validate against.")
    for npc in npcs:
        npc_id = npc.get("id", "?")
        cluster = str(npc.get("cluster", "")).strip()
        if cluster not in valid_clusters:
            raise ValueError(f"NPC {npc_id!r} references unknown cluster: {cluster!r}")


def load_all() -> dict[str, Any]:
    """
    Load everything in one call. Engine calls this at startup.
    Returns:
        {
            "npcs":         [list of NPC dicts],
            "tasks":        [list of task dicts],
            "interactions": {archetype_id: archetype_dict},
            "factions":     {org topology tree},
            "strings":      {nested flavor strings},
        }
    """
    factions = load_factions()
    npcs = load_npcs()
    _validate_npc_clusters_against_factions(npcs, factions)
    return {
        "npcs":         npcs,
        "tasks":        load_tasks(),
        "interactions": load_interactions(),
        "factions":     factions,
        "strings":      load_strings(),
    }

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.loader import (
    _REQUIRED_ARCHETYPE_FIELDS,
    _REQUIRED_NPC_FIELDS,
    _REQUIRED_TASK_FIELDS,
    _cluster_ids_from_factions,
)
from quests.definition import (
    DEFINITION_DIR,
    QuestDefinitionError,
    load_all_quest_definitions,
)


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "src" / "data"
SCENES_DIR = ROOT / "src" / "web" / "assets" / "Scenes"
PFPS_DIR = ROOT / "src" / "web" / "assets" / "PFPs"


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def validate_content() -> ValidationReport:
    report = ValidationReport()
    data = _load_data(report)
    if not data:
        return report

    _validate_npcs(report, data)
    _validate_tasks(report, data)
    _validate_archetypes(report, data)
    _validate_quest_definitions(report)
    return report


def _load_data(report: ValidationReport) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for name in ("npcs", "tasks", "interactions", "factions"):
        path = DATA_DIR / f"{name}.toml"
        try:
            with path.open("rb") as file:
                loaded[name] = tomllib.load(file)
        except Exception as exc:
            report.error(f"{path}: failed to load TOML: {exc}")
    return loaded


def _validate_npcs(report: ValidationReport, data: dict[str, Any]) -> None:
    npcs = data.get("npcs", {}).get("npcs", [])
    archetypes = data.get("interactions", {}).get("archetypes", [])
    factions = data.get("factions", {})
    archetype_ids = {str(item.get("id")) for item in archetypes if isinstance(item, dict)}
    cluster_ids = _cluster_ids_from_factions(factions)
    scene_files = _files(SCENES_DIR)
    pfp_files = _files(PFPS_DIR)

    if not isinstance(npcs, list) or not npcs:
        report.error("npcs.toml: expected at least one [[npcs]] record.")
        return

    ids = _find_duplicate_ids(npcs)
    for npc_id in ids:
        report.error(f"npcs.toml: duplicate NPC id {npc_id!r}.")

    for index, npc in enumerate(npcs):
        label = f"npcs[{index}] id={npc.get('id', '?')!r}"
        _require_fields(report, npc, _REQUIRED_NPC_FIELDS, label)
        npc_id = npc.get("id")
        if not _is_slug(npc_id):
            report.error(f"{label}: id must be a lowercase slug.")

        archetype = npc.get("archetype")
        if archetype not in archetype_ids:
            report.error(f"{label}: unknown archetype {archetype!r}.")

        cluster = str(npc.get("cluster", "")).strip()
        if cluster and cluster not in cluster_ids:
            report.error(f"{label}: unknown faction cluster {cluster!r}.")

        _validate_string_list(report, npc.get("influence_scope"), f"{label}.influence_scope")
        _validate_string_list(report, npc.get("access_tags"), f"{label}.access_tags")
        _validate_string_list(report, npc.get("prompt_templates"), f"{label}.prompt_templates", required=False)
        _validate_int_range(report, npc.get("ambition"), f"{label}.ambition", 0, 10)
        _validate_int_range(report, npc.get("base_trust"), f"{label}.base_trust", 0, 100)
        _validate_int_range(report, npc.get("base_rivalry"), f"{label}.base_rivalry", 0, 100)
        _validate_int_range(report, npc.get("influence_weight"), f"{label}.influence_weight", 0, 10)

        scene = npc.get("watercooler_scene")
        if scene and scene not in scene_files:
            report.error(f"{label}: missing watercooler_scene asset {scene!r}.")
        elif not scene:
            report.warn(f"{label}: no watercooler_scene set; random watercooler routing may skip this NPC.")

        pfp = npc.get("pfp")
        if pfp and pfp not in pfp_files:
            report.error(f"{label}: missing pfp asset {pfp!r}.")
        elif not pfp:
            report.warn(f"{label}: no pfp asset set.")

        if npc.get("watercooler_pool", True) is not False:
            seed = npc.get("watercooler_seed")
            if not isinstance(seed, str) or not seed.strip():
                report.error(f"{label}: watercooler_pool NPCs require watercooler_seed.")


def _validate_tasks(report: ValidationReport, data: dict[str, Any]) -> None:
    tasks = data.get("tasks", {}).get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        report.error("tasks.toml: expected at least one [[tasks]] record.")
        return

    for task_id in _find_duplicate_ids(tasks):
        report.error(f"tasks.toml: duplicate task id {task_id!r}.")

    for index, task in enumerate(tasks):
        label = f"tasks[{index}] id={task.get('id', '?')!r}"
        _require_fields(report, task, _REQUIRED_TASK_FIELDS, label)
        if not _is_slug(task.get("id")):
            report.error(f"{label}: id must be a lowercase slug.")
        for key in ("energy_cost", "deadline_days", "reward_rep", "reward_money", "risk_stress", "fallback_dc"):
            if type(task.get(key)) is not int:
                report.error(f"{label}.{key}: must be an integer.")


def _validate_archetypes(report: ValidationReport, data: dict[str, Any]) -> None:
    archetypes = data.get("interactions", {}).get("archetypes", [])
    if not isinstance(archetypes, list) or not archetypes:
        report.error("interactions.toml: expected at least one [[archetypes]] record.")
        return

    for archetype_id in _find_duplicate_ids(archetypes):
        report.error(f"interactions.toml: duplicate archetype id {archetype_id!r}.")

    for index, archetype in enumerate(archetypes):
        label = f"archetypes[{index}] id={archetype.get('id', '?')!r}"
        _require_fields(report, archetype, _REQUIRED_ARCHETYPE_FIELDS, label)
        if not _is_slug(archetype.get("id")):
            report.error(f"{label}: id must be a lowercase slug.")
        _validate_string_list(report, archetype.get("templates"), f"{label}.templates")
        if not isinstance(archetype.get("outcome_hints"), str) or not archetype["outcome_hints"].strip():
            report.error(f"{label}.outcome_hints: must be non-empty text.")


def _validate_quest_definitions(report: ValidationReport) -> None:
    try:
        definitions = load_all_quest_definitions(include_disabled=True)
    except (OSError, QuestDefinitionError, ValueError) as exc:
        report.error(f"{DEFINITION_DIR}: quest definition validation failed: {exc}")
        return
    if not definitions:
        report.warn(f"{DEFINITION_DIR}: no quest definitions found.")


def _require_fields(report: ValidationReport, record: dict[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - set(record))
    if missing:
        report.error(f"{label}: missing required fields {missing}.")


def _validate_string_list(report: ValidationReport, value: Any, label: str, required: bool = True) -> None:
    if value is None and not required:
        return
    if not isinstance(value, list) or not value:
        report.error(f"{label}: must be a non-empty string list.")
        return
    for item in value:
        if not isinstance(item, str) or not item.strip():
            report.error(f"{label}: contains a non-string or empty item.")
            return


def _validate_int_range(report: ValidationReport, value: Any, label: str, low: int, high: int) -> None:
    if type(value) is not int or not low <= value <= high:
        report.error(f"{label}: must be an integer between {low} and {high}.")


def _find_duplicate_ids(records: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        item_id = record.get("id")
        if item_id in seen:
            duplicates.add(str(item_id))
        seen.add(item_id)
    return sorted(duplicates)


def _files(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {item.name for item in path.iterdir() if item.is_file()}


def _is_slug(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip() and value.replace("_", "").isalnum()

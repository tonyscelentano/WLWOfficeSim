"""
state_models.py — Pure dataclasses for OfficeSim game state.

Passive data containers only — no mutation logic.
GameState (state.py) owns all writes; systems read via snapshot() or targeted getters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Task Instance ─────────────────────────────────────────────────────────────
@dataclass
class TaskInstance:
    """
    A live task in the player's queue. Forked from a task template at assignment time.
    The TOML template is immutable; this object carries all mutable runtime fields.
    """
    template_id: str
    title: str
    task_type: str          # "internal" | "client"
    required_skill: str
    energy_cost: int
    reward_rep: int
    reward_money: int
    risk_stress: int
    fallback_dc: int
    prompt_template: str
    evaluation_hint: str
    days_remaining: int                    # counts down each end-of-day tick
    completed: bool = False
    outcome: str | None = None             # dumpster_fire | partial | success | legendary

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TaskInstance":
        return cls(**d)


# ── NPC Relationship ──────────────────────────────────────────────────────────
@dataclass
class NPCRelationship:
    """
    Runtime relationship state for one NPC.
    Trust and rivalry are independent axes — a high-trust rival is absolutely a thing.
    Seeded from npcs.toml base_trust / base_rivalry at game start.
    """
    npc_id: str
    name: str = "Unknown"
    role: str = "Unknown"
    pfp: str | None = None
    trust: int = 50      # 0–100
    rivalry: int = 0     # 0–100
    interactions: int = 0   # total logged interactions (hooks for career/social events)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "NPCRelationship":
        return cls(**d)


# ── Player State ──────────────────────────────────────────────────────────────
@dataclass
class PlayerState:
    # Identity — populated during onboarding (job application flow)
    name: str = "Player"
    department: str | None = None   # None = free agent until onboarding complete
    reports_to: str | None = None
    title: str = "New Hire"

    # Core stats — all mutations go through GameState.apply_delta()
    energy: int = 100
    stress: int = 0
    reputation: int = 50
    money: int = 2_000
    xp: int = 0

    # Skills — keyed by required_skill values used in task/interaction templates
    skills: dict[str, int] = field(default_factory=lambda: {
        "engineering": 1,
        "communication": 1,
        "politics": 1,
    })

    # Game progression
    day: int = 1

    # Real-time presence tracking.
    # game_time is derived from wall clock on each engine tick — not stored as a counter.
    # session_start: ISO timestamp of when the player launched this session.
    # day_start_time: minutes-since-midnight of first action today ("arrived").
    # day_end_time: minutes-since-midnight when player quit for the day. None = still here.
    # hr_lockout_until: minutes-since-midnight when HR ban lifts. None = not locked out.
    # presence_log: one entry per completed day for trait computation.
    session_start: str | None = None
    day_start_time: int | None = None
    day_end_time: int | None = None
    hr_lockout_until: int | None = None
    presence_log: list[dict] = field(default_factory=list)

    # HR Metrics & Warnings
    hr_warnings: list[str] = field(default_factory=list)
    pitch_fail_count: int = 0
    watercooler_time: int = 0  # tracks context-minutes spent in social scenes
    tutorial_done: bool = False

    # Live collections
    active_tasks: list[TaskInstance] = field(default_factory=list)
    relationships: dict[str, NPCRelationship] = field(default_factory=dict)
    social_log: list[dict] = field(default_factory=list)  # tracks recent NPC conversations
    quests: dict[str, Any] = field(default_factory=dict)  # tracks side-quest progress
    unlocks: list[str] = field(default_factory=list)        # earned access tokens (e.g. "cto_badge")

    def to_dict(self) -> dict[str, Any]:
        return {
            **{k: v for k, v in self.__dict__.items()
               if k not in ("active_tasks", "relationships")},
            "active_tasks": [t.to_dict() for t in self.active_tasks],
            "relationships": {k: v.to_dict() for k, v in self.relationships.items()},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PlayerState":
        raw = dict(d)
        tasks = [TaskInstance.from_dict(t) for t in raw.pop("active_tasks", [])]
        rels = {k: NPCRelationship.from_dict(v) for k, v in raw.pop("relationships", {}).items()}
        filtered = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
        obj = cls(**filtered)
        obj.active_tasks = tasks
        obj.relationships = rels
        return obj

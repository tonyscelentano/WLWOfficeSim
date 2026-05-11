"""
state.py — Passive Game State (The Save File / The Database)

Owns:
  - Player stats with invariant clamping via apply_delta()
  - Runtime NPC relationship values (trust, rivalry) — TOML values are starting templates
  - Active task instances — TOML values are task factories, not live objects
  - Game phase and day counter
  - Save/load with versioned schema and slot management.

Data models live in state_models.py (TaskInstance, NPCRelationship, PlayerState).

Contract:
  - Only engine.py calls mutating methods.
  - Systems (tasks, social, career) call snapshot() or read player fields; they never write.
  - Persistence is JSON wrapped in a versioned envelope. TOML data files are read-only
    templates; state owns the runtime copy.

Save schema (SCHEMA_VERSION = 1):
  {
    "schema_version": 1,
    "saved_at":       <ISO timestamp>,
    "slot":           <int>,
    "save_name":      "<player> — Day N",
    "meta":           { application: {...}, onboarding_result: {...} },
    "player":         { ...PlayerState.to_dict()... }
  }

Bloat policy:
  - presence_log is trimmed to the last MAX_PRESENCE_LOG_ENTRIES rows on every save.
  - Anything else that grows unbounded must declare a retention rule here.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

# Re-exported so callers doing `from core.state import TaskInstance` keep working.
from core.state_models import NPCRelationship, PlayerState, TaskInstance  # noqa: F401

log = logging.getLogger(__name__)

# ── Save schema ──────────────────────────────────────────────────────────────

SCHEMA_VERSION = 1
# state.py lives at <root>/src/core/state.py — three parents up is the project root.
SAVES_DIR = Path(__file__).resolve().parent.parent.parent / "Saves"
SAVE_SLOTS = (0, 1, 2, 3, 4)         # slot 0 = autosave; 1–4 reserved for manual saves
AUTOSAVE_SLOT = 0
MAX_PRESENCE_LOG_ENTRIES = 30        # rolling window — older days are pruned on save
MAX_SOCIAL_LOG_ENTRIES = 20          # keep recent chat history for LLM context


def slot_path(slot: int) -> Path:
    return SAVES_DIR / f"slot{int(slot)}.json"


# ── Stat bounds ───────────────────────────────────────────────────────────────
# All player stats are clamped to these ranges on every mutation.
STAT_BOUNDS: dict[str, tuple[int, int]] = {
    "energy":     (0, 100),
    "stress":     (0, 100),
    "reputation": (0, 200),
    "money":      (0, 999_999),
    "xp":         (0, 999_999),
}


def _clamp(value: int, stat: str) -> int:
    lo, hi = STAT_BOUNDS.get(stat, (0, 999_999))
    return max(lo, min(hi, value))


# ── GameState ─────────────────────────────────────────────────────────────────
class GameState:
    """
    Single source of truth. Engine.py is the only authorized caller of mutating methods.
    Systems and UI read via snapshot() or targeted getters — never raw attribute access.
    """

    def __init__(self) -> None:
        self.player = PlayerState()
        # Set by load_slot() so engine/server can know which slot is current.
        self.last_loaded_slot: int | None = None
        self.last_loaded_meta: dict[str, Any] = {}
        self.version = 0
        
    def bump_version(self) -> None:
        self.version += 1

    # ── Stat mutation (engine-only) ───────────────────────────────────────────

    def apply_delta(self, deltas: dict[str, int]) -> dict[str, int]:
        """
        Apply {stat: delta} pairs to the player.
        Clamps each result to STAT_BOUNDS.
        Returns actual applied changes (post-clamp), useful for UI diff display.
        """
        applied: dict[str, int] = {}
        for stat, delta in deltas.items():
            if not hasattr(self.player, stat):
                log.warning("apply_delta: unknown stat '%s' — skipped.", stat)
                continue
            old: int = getattr(self.player, stat)
            new = _clamp(old + delta, stat)
            setattr(self.player, stat, new)
            applied[stat] = new - old
        return applied

    def is_burnt_out(self) -> bool:
        """HR safety check: Player is medically unfit for work."""
        return self.player.energy <= 5 or self.player.stress >= 95

    def add_hr_warning(self, msg: str) -> None:
        if msg not in self.player.hr_warnings:
            self.player.hr_warnings.append(msg)

    def clear_hr_warnings(self) -> None:
        self.player.hr_warnings.clear()

    def apply_skill_delta(self, skill: str, delta: int) -> int:
        """Mutate a skill value. Skills floor at 0, no ceiling at MVP. Returns actual change."""
        old = self.player.skills.get(skill, 0)
        new = max(0, old + delta)
        self.player.skills[skill] = new
        return new - old

    # ── Task management ───────────────────────────────────────────────────────

    def add_task(self, task: TaskInstance) -> None:
        self.player.active_tasks.append(task)

    def remove_task(self, template_id: str) -> None:
        self.player.active_tasks = [
            t for t in self.player.active_tasks if t.template_id != template_id
        ]

    def tick_deadlines(self) -> list[TaskInstance]:
        """
        End-of-day deadline tick.
        Decrements days_remaining on all incomplete tasks.
        Returns list of newly expired tasks (days_remaining hit 0 this tick).
        Engine decides what to do with them (auto-fail, warn, etc.).
        """
        expired: list[TaskInstance] = []
        for task in self.player.active_tasks:
            if not task.completed:
                task.days_remaining -= 1
                if task.days_remaining <= 0:
                    expired.append(task)
        return expired

    # ── Relationship management ───────────────────────────────────────────────

    def init_relationship(self, npc_id: str, name: str, role: str, pfp: str | None, trust: int, rivalry: int) -> None:
        """Seed a relationship from TOML template values."""
        self.player.relationships[npc_id] = NPCRelationship(
            npc_id=npc_id,
            name=name,
            role=role,
            pfp=pfp,
            trust=trust,
            rivalry=rivalry,
        )

    def update_relationship(
        self,
        npc_id: str,
        trust_delta: int = 0,
        rivalry_delta: int = 0,
    ) -> None:
        rel = self.player.relationships.get(npc_id)
        if rel is None:
            log.warning("update_relationship: unknown NPC '%s' — skipped.", npc_id)
            return
        rel.trust = max(0, min(100, rel.trust + trust_delta))
        rel.rivalry = max(0, min(100, rel.rivalry + rivalry_delta))
        rel.interactions += 1

    # ── Presence / clock management ──────────────────────────────────────────

    @staticmethod
    def _now_minutes() -> int:
        """Current wall-clock time as minutes since midnight."""
        now = datetime.now()
        return now.hour * 60 + now.minute

    def clock_in(self) -> None:
        """Record session start and first-action arrival time if not already set."""
        now_iso = datetime.now().isoformat()
        if self.player.session_start is None:
            self.player.session_start = now_iso
        if self.player.day_start_time is None:
            self.player.day_start_time = self._now_minutes()

    def clock_out(self) -> None:
        """Record departure time for the day."""
        self.player.day_end_time = self._now_minutes()

    def log_day_presence(self) -> None:
        """
        Append today's presence record to the log and reset daily trackers.
        Called by engine at end-of-day. Presence log is what trait engine reads.
        """
        arrived = self.player.day_start_time or self._now_minutes()
        left = self.player.day_end_time or self._now_minutes()
        minutes_active = max(0, left - arrived)
        self.player.presence_log.append({
            "day": self.player.day,
            "arrived": arrived,
            "left": left,
            "minutes_active": minutes_active,
        })
        self.player.day_start_time = None
        self.player.day_end_time = None
        self.player.hr_lockout_until = None
        self.player.watercooler_time = 0

    def set_hr_lockout(self, duration_minutes: int) -> None:
        """Lock the player out of work actions for duration_minutes real time."""
        release_at = self._now_minutes() + duration_minutes
        self.player.hr_lockout_until = release_at
        log.info("HR lockout set until minute %d.", release_at)

    def is_hr_locked(self) -> bool:
        """True if the player is currently under an HR-imposed work ban."""
        if self.player.hr_lockout_until is None:
            return False
        return self._now_minutes() < self.player.hr_lockout_until

    def advance_day(self) -> None:
        self.player.day += 1

    # ── Persistence ───────────────────────────────────────────────────────────

    def _trim_bloat(self) -> None:
        """Apply schema-driven retention rules to in-memory player state."""
        log_entries = self.player.presence_log
        if len(log_entries) > MAX_PRESENCE_LOG_ENTRIES:
            self.player.presence_log = log_entries[-MAX_PRESENCE_LOG_ENTRIES:]
            
        social_entries = self.player.social_log
        if len(social_entries) > MAX_SOCIAL_LOG_ENTRIES:
            self.player.social_log = social_entries[-MAX_SOCIAL_LOG_ENTRIES:]

    def save_slot(self, slot: int = AUTOSAVE_SLOT, meta: dict[str, Any] | None = None) -> Path:
        """
        Write the current state to <SAVES_DIR>/slot<N>.json using the v1 envelope.
        If meta is None and the slot already has a save, the existing meta is preserved
        — autosaves don't lose application/onboarding context.
        """
        if slot not in SAVE_SLOTS:
            raise ValueError(f"Unknown save slot {slot}; valid slots are {SAVE_SLOTS}")
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        self._trim_bloat()
        target = slot_path(slot)

        if meta is None:
            # Carry forward whatever meta was last attached to this slot.
            try:
                with target.open(encoding="utf-8") as f:
                    prior = json.load(f)
                meta = dict(prior.get("meta") or {})
            except (FileNotFoundError, json.JSONDecodeError):
                meta = dict(self.last_loaded_meta or {})

        envelope = {
            "schema_version": SCHEMA_VERSION,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "slot": slot,
            "save_name": f"{self.player.name} — Day {self.player.day}",
            "meta": meta,
            "player": self.player.to_dict(),
        }
        with target.open("w", encoding="utf-8") as f:
            json.dump(envelope, f, indent=2)
        log.info("Saved → slot%d (Day %d)", slot, self.player.day)
        return target

    def load_slot(self, slot: int) -> dict[str, Any]:
        """
        Replace self.player with the contents of slot<N>.json.
        Returns the envelope's `meta` dict so the server can restore session globals.
        Raises FileNotFoundError if the slot is empty, ValueError if the schema
        version is newer than this build understands.
        """
        if slot not in SAVE_SLOTS:
            raise ValueError(f"Unknown save slot {slot}; valid slots are {SAVE_SLOTS}")
        target = slot_path(slot)
        if not target.exists():
            raise FileNotFoundError(f"No save at slot {slot}")
        with target.open(encoding="utf-8") as f:
            envelope = json.load(f)

        version = int(envelope.get("schema_version", 0))
        if version > SCHEMA_VERSION:
            raise ValueError(
                f"Save slot {slot} was written with schema_version={version}, "
                f"newer than this build (v{SCHEMA_VERSION}). Refusing to load."
            )
        # v0 saves (no envelope) are not supported — none exist in the wild.
        if version < 1 or "player" not in envelope:
            raise ValueError(
                f"Save slot {slot} is in a legacy/unknown format and cannot be loaded."
            )

        self.player = PlayerState.from_dict(envelope["player"])
        self.last_loaded_slot = slot
        self.last_loaded_meta = dict(envelope.get("meta") or {})
        log.info("Loaded ← slot%d (Day %d)", slot, self.player.day)
        return self.last_loaded_meta

    # Legacy helpers — keep working for callers that still write to a default slot.
    def save(self, path: Path | None = None) -> None:
        if path is None:
            self.save_slot(AUTOSAVE_SLOT)
            return
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.player.to_dict(), f, indent=2)
        log.info("Saved → %s", path)

    def load(self, path: Path | None = None) -> None:
        if path is None:
            try:
                self.load_slot(AUTOSAVE_SLOT)
            except FileNotFoundError:
                log.info("No autosave — fresh game.")
            return
        if not path.exists():
            log.info("No save at %s — fresh game.", path)
            return
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        # Tolerate raw player dicts at explicit paths (legacy/test fixtures).
        if "player" in data and "schema_version" in data:
            self.player = PlayerState.from_dict(data["player"])
        else:
            self.player = PlayerState.from_dict(data)
        log.info("Loaded ← %s (Day %d)", path, self.player.day)

    # ── Read interface ────────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """
        Full serializable read-only view of player state.
        Systems and UI consume this — never touch self.player attributes directly.
        """
        return self.player.to_dict()


def list_saves() -> list[dict[str, Any]]:
    """
    Inspect SAVES_DIR and return one summary dict per occupied slot.
    Caller (server) uses this for /api/saves.
    """
    summaries: list[dict[str, Any]] = []
    for slot in SAVE_SLOTS:
        path = slot_path(slot)
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8") as f:
                envelope = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Skipping unreadable save at slot %d: %s", slot, exc)
            continue
        player = envelope.get("player") or {}
        summaries.append({
            "slot": slot,
            "save_name": envelope.get("save_name") or f"slot{slot}",
            "saved_at": envelope.get("saved_at"),
            "schema_version": envelope.get("schema_version", 0),
            "player_name": player.get("name", "Unknown"),
            "day": player.get("day", 1),
            "title": player.get("title"),
            "department": player.get("department"),
            "is_autosave": slot == AUTOSAVE_SLOT,
        })
    return summaries

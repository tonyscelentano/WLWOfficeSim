"""
engine.py — Active Game Orchestrator (The Ruleset and the Clock)

Owns:
  - Real-time tick loop (1 real minute = 1 game minute)
  - Action resolution: player input → system call → state delta → bus event
  - HR intervention logic: stress threshold monitoring and lockout enforcement
  - End-of-day logic: midnight rollover, presence logging, deadline ticks
  - TOML data seeding: calls loader, hydrates initial GameState on new game
  - Adapter-backed bus routing: forwards career-relevant events through
    systems.adapter.dispatch and applies any returned Result.

Contract:
  - Only engine writes to state. Systems return Result dicts; engine applies them.
  - All inter-system communication goes through the bus, not direct calls.
  - Result dicts conform to systems.result_contract; _apply_result normalizes
    every payload before mutating state.
  - The web frontend calls engine.handle_action(verb, **kwargs) via /api/action.

Tick rate:
  TICK_SECONDS = 60 (1 real minute). Lower for testing. Never below 1.
"""
from __future__ import annotations

import logging
import random
import time
from datetime import datetime
from typing import Any, Callable

from systems import adapter

from core.action_scenes import apply_action_scene
from core.bus import bus
from core.loader import load_all
from core.presence import publish_presence_trait
from core.social_resolver import SocialResolver
from core.state import GameState, TaskInstance
from systems.adapter import dispatch as adapter_dispatch
from systems.result_contract import normalize_result

log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

TICK_SECONDS = 60          # 1 real minute per tick. Tune for testing.

HR_STRESS_THRESHOLD = 80   # Stress at or above this triggers HR intervention.
HR_LOCKOUT_MINUTES  = 30   # Real minutes the player cannot take work actions.

MIDNIGHT = 1440            # Minutes since midnight at day rollover.
PASSIVE_STRESS_PER_TICK = 1   # Stress added per tick while working (not locked out).
PASSIVE_RECOVERY_PER_TICK = 2 # Stress removed per tick while HR-locked (forced break).

AUTOSAVE_INTERVAL_SECONDS = 600  # Real-time auto-save cadence (10 minutes).

# Bus events the career system subscribes to via the adapter. When engine
# publishes any of these, _route_to_career forwards them through
# adapter.dispatch and applies any returned Result via _apply_result.
CAREER_BUS_EVENTS = (
    "task_failed",
    "task_resolved",
    "presence_trait_updated",
    "random_politics",
)


# Result dict shape is defined in systems.result_contract.RESULT_DEFAULTS.
# _apply_result calls normalize_result() before mutating state, so missing
# keys are filled with zeros and unknown keys are dropped silently.


class Engine:
    """
    Instantiate once. Pass to Textual app. Call start() after app mounts.
    The Textual app owns the set_interval call — engine exposes tick() as the target.
    """

    def __init__(self) -> None:
        self.state = GameState()
        self.data: dict[str, Any] = {}     # hydrated TOML templates
        self._initialized = False
        self._last_autosave_at: float = 0.0  # monotonic seconds; 0 = never
        self._wire_career_bus_routing()

    # ── Startup ───────────────────────────────────────────────────────────────

    def new_game(self, player_name: str) -> None:
        """
        Initialize a fresh game state from TOML templates.
        Called after onboarding (job application) flow completes.
        """
        self.data = load_all()
        self.state = GameState()
        self.state.player.name = player_name
        self.state.clock_in()

        # (NPC relationships are no longer seeded here. They unlock when met.)
        
        # Seed initial task queue (one of each template for MVP).
        for task_tmpl in self.data["tasks"]:
            self.state.add_task(self._instantiate_task(task_tmpl))

        self._initialized = True
        self._last_autosave_at = time.monotonic()
        bus.publish("game_started", {"player": player_name})
        log.info("New game started for '%s'.", player_name)

    def load_game(self, slot: int | None = None) -> dict[str, Any]:
        """
        Load an existing save into the engine. Returns the meta dict from the save
        envelope so the caller (server) can restore session-level state. Reloads TOML
        templates (never persisted in saves).
        """
        self.data = load_all()
        if slot is None:
            self.state.load()           # legacy default-slot path
            meta: dict[str, Any] = dict(self.state.last_loaded_meta or {})
        else:
            meta = self.state.load_slot(slot)

        # Migrate old saves and always sync latest visual data from templates.
        # Since the NPC Studio allows editing these fields, we force-sync them
        # on load so the save doesn't hold stale UI data.
        npc_lookup = {n["id"]: n for n in self.data.get("npcs", [])}
        for npc_id, rel in self.state.player.relationships.items():
            if npc_id in npc_lookup:
                rel.name = npc_lookup[npc_id].get("name", "Unknown")
                rel.role = npc_lookup[npc_id].get("role", "Unknown")
                rel.pfp = npc_lookup[npc_id].get("pfp")

        self._initialized = True
        self._last_autosave_at = time.monotonic()
        bus.publish("game_loaded", self.state.snapshot())
        return meta

    # ── Real-time tick (Textual calls this via set_interval) ──────────────────

    def tick(self) -> None:
        """
        Called every TICK_SECONDS by the Textual app.
        Advances game clock, applies passive stat changes, checks thresholds.
        """
        if not self._initialized:
            return

        now = datetime.now()
        game_time = now.hour * 60 + now.minute

        # Midnight rollover.
        if game_time == 0 and self.state.player.day_start_time is not None:
            self._end_of_day()
            return

        # Passive stat changes.
        if self.state.is_hr_locked():
            # Forced break: stress recovers passively.
            self.state.apply_delta({"stress": -PASSIVE_RECOVERY_PER_TICK})
            bus.publish("tick", {"game_time": game_time, "hr_locked": True})
            # Lift lockout if stress has recovered enough to be worth it.
            if self.state.player.stress <= 40:
                self._lift_hr_lockout(game_time)
        else:
            # Normal working tick: passive stress accumulates.
            self.state.apply_delta({"stress": PASSIVE_STRESS_PER_TICK})
            self._check_hr_threshold()
            bus.publish("tick", {"game_time": game_time, "hr_locked": False})
            
        self.state.bump_version()

        self._maybe_autosave()

    def _maybe_autosave(self) -> None:
        """
        Write to the autosave slot if at least AUTOSAVE_INTERVAL_SECONDS of real time
        have passed since the last save. Failures are logged but never raised — a
        broken disk should not crash the tick loop.
        """
        now = time.monotonic()
        if self._last_autosave_at and (now - self._last_autosave_at) < AUTOSAVE_INTERVAL_SECONDS:
            return
        try:
            self.state.save_slot()  # default = autosave slot, preserves existing meta
            self._last_autosave_at = now
            bus.publish("autosaved", {"day": self.state.player.day})
        except Exception:
            log.exception("Autosave failed.")

    def _s(self, section: str, key: str, default: str = "", **kwargs: Any) -> str:
        """Helper to retrieve flavor strings from TOML data."""
        tmpl = self.data.get("strings", {}).get(section, {}).get(key, default)
        try:
            return tmpl.format(**kwargs)
        except Exception:
            return tmpl

    # ── Action resolution ─────────────────────────────────────────────────────

    def handle_action(self, verb: str, **kwargs: Any) -> dict[str, Any]:
        """
        Entry point for all player actions from the UI.
        Returns a result dict for the UI to display. Never raises to the caller.

        Verbs: "work" | "socialize" | "learn" | "slack" | "recover" | "quit_for_day"
        """
        if not self._initialized:
            return {"outcome": "error", "flavor": self._s("engine", "not_initialized", "Game not initialized.")}

        # Gate: work actions blocked during HR lockout.
        if verb in ("work", "learn") and self.state.is_hr_locked():
            return {
                "outcome": "blocked",
                "flavor": self._s("engine", "hr_blocked", "HR has asked you to step away."),
            }


        # Gate: clock in on first action of the day.
        self.state.clock_in()

        handlers = {
            "work":         self._resolve_work,
            "socialize":    self._resolve_socialize,
            "learn":        self._resolve_learn,
            "slack":        self._resolve_slack,
            "recover":      self._resolve_recover,
            "quit_for_day": self._resolve_quit,
            "visit_it":     self._resolve_visit_it,
        }

        handler = handlers.get(verb)
        if handler is None:
            log.warning("Unknown action verb '%s'.", verb)
            return {"outcome": "error", "flavor": self._s("engine", "unknown_action", verb=verb)}

        try:
            result = handler(**kwargs)
        except Exception:
            log.exception("Action '%s' raised unexpectedly.", verb)
            return {"outcome": "error", "flavor": self._s("engine", "something_broke")}

        self._apply_result(result)
        apply_action_scene(result, verb, self.state.player.stress, log)

        self.state.bump_version()
        return result

    # ── Action handlers ───────────────────────────────────────────────────────

    def _resolve_work(self, task_id: str | None = None, player_input: str = "") -> dict:
        """
        Resolve a work action against the task queue.
        If task_id is None, picks the highest-stakes active task.
        Calls the LLM evaluator (tasks system) via the adapter.
        """
        task = self._find_task(task_id)
        if task is None:
            return {"outcome": "partial", "flavor": self._s("engine", "no_tasks")}

        skill_level = self.state.player.skills.get(task.required_skill, 1)
        
        # Route through adapter
        response = adapter.dispatch({
            "system": "tasks",
            "action": "resolve",
            "payload": {
                "task": task.to_dict() if hasattr(task, "to_dict") else task,
                "player_input": player_input,
                "skill_level": skill_level,
            }
        })
        result = response.get("result") or {"outcome": "error", "flavor": self._s("engine", "adapter_failed")}

        # Mark task complete regardless of outcome — it was attempted.
        task.completed = True
        task.outcome = result.get("outcome")
        self.state.remove_task(task.template_id)

        bus.publish("task_resolved", {
            "task_id": task.template_id,
            "outcome": result.get("outcome"),
            "flavor": result.get("flavor"),
        })
        return result

    def _resolve_visit_it(self, **kwargs: Any) -> dict[str, Any]:
        """Specific socialization entry for the IT basement."""
        return self._resolve_socialize(npc_id="jason_it", force_quest_offer=True)

    def _resolve_socialize(
        self,
        npc_id: str,
        player_input: str = "",
        force_quest_offer: bool = False,
    ) -> dict:
        """Resolve a social interaction with an NPC via the adapter."""
        return SocialResolver(self.state, self.data, self._s).resolve(
            npc_id=npc_id,
            player_input=player_input,
            force_quest_offer=force_quest_offer,
        )

    def _resolve_learn(self, skill: str = "engineering") -> dict:
        """Spend energy to gain XP in a skill. No LLM needed."""
        cost = 15
        gain = random.randint(1, 3)
        return {
            "outcome": "success",
            "flavor": self._s("engine", "learn_flavor", skill=skill),
            "energy_delta": -cost,
            "stress_delta": 2,
            "xp_delta": gain * 10,
            "skill_deltas": {skill: gain},
        }

    def _resolve_slack(self, **kwargs: Any) -> dict:
        """Browse the internet or play games. Triggers minigame UI."""
        game_type = random.choice(["tetris", "meeting_dodge"])

        return {
            "outcome": "success",
            "flavor": self._s("engine", "slack_flavor", game=game_type.capitalize()),
            "minigame": game_type
        }


    def _resolve_recover(self) -> dict:
        """Step away: coffee, walk, stare at wall. Energy and stress recovery."""
        return {
            "outcome": "success",
            "flavor": self._s("engine", "coffee_flavor"),
            "energy_delta": 15,
            "stress_delta": -12,
        }

    def _resolve_quit(self) -> dict:
        """Player voluntarily ends their workday."""
        self.state.clock_out()
        self._end_of_day()
        return {
            "outcome": "success",
            "flavor": self._s("engine", "logout_flavor"),
        }

    # ── HR intervention ───────────────────────────────────────────────────────

    def _check_hr_threshold(self) -> None:
        if self.state.player.stress >= HR_STRESS_THRESHOLD:
            self.state.set_hr_lockout(HR_LOCKOUT_MINUTES)
            bus.publish("hr_intervention", {
                "stress": self.state.player.stress,
                "lockout_minutes": HR_LOCKOUT_MINUTES,
                "flavor": self._s("engine", "hr_intervention_flavor", minutes=HR_LOCKOUT_MINUTES),
            })

    def _lift_hr_lockout(self, game_time: int) -> None:
        self.state.player.hr_lockout_until = None
        bus.publish("hr_lockout_lifted", {
            "game_time": game_time,
            "stress": self.state.player.stress,
        })

    # ── End of day ────────────────────────────────────────────────────────────

    def _end_of_day(self) -> None:
        """
        Midnight rollover or voluntary quit.
        Ticks deadlines, logs presence, advances day counter, saves.
        """
        expired = self.state.tick_deadlines()
        for task in expired:
            self.state.apply_delta({"stress": task.risk_stress, "rep_delta": -5})
            bus.publish("task_failed", {
                "task_id": task.template_id,
                "flavor": f"'{task.title}' deadline hit. It auto-closed. Someone noticed.",
            })

        self.state.log_day_presence()
        publish_presence_trait(self.state)
        self.state.advance_day()
        self.state.save()

        bus.publish("day_ended", {
            "day": self.state.player.day,
            "presence_log": self.state.player.presence_log[-1]
                            if self.state.player.presence_log else {},
        })

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _instantiate_task(self, tmpl: dict[str, Any]) -> TaskInstance:
        return TaskInstance(
            template_id=tmpl["id"],
            title=tmpl["title"],
            task_type=tmpl["task_type"],
            required_skill=tmpl["required_skill"],
            energy_cost=tmpl["energy_cost"],
            reward_rep=tmpl["reward_rep"],
            reward_money=tmpl["reward_money"],
            risk_stress=tmpl["risk_stress"],
            fallback_dc=tmpl["fallback_dc"],
            prompt_template=tmpl["prompt_template"],
            evaluation_hint=tmpl["evaluation_hint"],
            days_remaining=tmpl["deadline_days"],
        )

    def _find_task(self, task_id: str | None) -> TaskInstance | None:
        tasks = self.state.player.active_tasks
        if not tasks:
            return None
        if task_id:
            return next((t for t in tasks if t.template_id == task_id), None)
        # Default: highest stress risk (most dangerous deadline).
        return max(tasks, key=lambda t: t.risk_stress)

    def _apply_result(self, result: dict[str, Any]) -> None:
        """Apply a system result dict to state. Engine is the only writer."""
        normalized = normalize_result(result)
        self.state.apply_delta({
            "energy":     normalized["energy_delta"],
            "stress":     normalized["stress_delta"],
            "reputation": normalized["rep_delta"],
            "money":      normalized["money_delta"],
            "xp":         normalized["xp_delta"],
        })

        for skill, delta in normalized["skill_deltas"].items():
            self.state.apply_skill_delta(skill, delta)

        for npc_id, rel_delta in normalized["npc_deltas"].items():
            self.state.update_relationship(
                npc_id=npc_id,
                trust_delta=rel_delta.get("trust", 0),
                rivalry_delta=rel_delta.get("rivalry", 0),
            )

    # ── Adapter-backed bus routing ────────────────────────────────────────────

    def _wire_career_bus_routing(self) -> None:
        """
        Subscribe a router for each event the career system listens to.
        The bus delivers only the payload to subscribers, so we capture the
        event name in a per-event closure.
        """
        self._career_routers: list[tuple[str, Any]] = []
        for event_name in CAREER_BUS_EVENTS:
            router = self._make_career_router(event_name)
            self._career_routers.append((event_name, router))
            bus.subscribe(event_name, router)

    def reset_career_bus(self) -> None:
        """Unsubscribe all career routers and re-wire. Call on logout to prevent accumulation."""
        for event_name, router in getattr(self, '_career_routers', []):
            bus.unsubscribe(event_name, router)
        self._wire_career_bus_routing()

    def _make_career_router(self, event_name: str) -> Callable[[dict[str, Any]], None]:
        def _route(payload: dict[str, Any]) -> None:
            self._route_to_career(event_name, payload)
        _route.__qualname__ = f"Engine._route_to_career[{event_name}]"
        return _route

    def _route_to_career(self, event_name: str, payload: dict[str, Any]) -> None:
        """
        Forward a bus event through the systems adapter and apply any returned
        Result. Runs synchronously inside bus.publish — the bus already isolates
        subscriber exceptions, so we don't need a second try/except here.
        """
        if not self._initialized:
            return
        response = adapter_dispatch({
            "system": "career",
            "action": "handle_bus_event",
            "payload": {"event_name": event_name, "event_data": dict(payload or {})},
            "player_snapshot": self.state.snapshot(),
        })
        if not response.get("ok"):
            log.warning(
                "Adapter rejected career routing for '%s': %s",
                event_name, response.get("error"),
            )
            return
        if response.get("kind") == "result" and response.get("result"):
            self._apply_result(response["result"])

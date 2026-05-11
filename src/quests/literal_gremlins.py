from __future__ import annotations

from typing import Any

from quests.definition import load_quest_definition
from core.llm import call_llm_json
from core.state import GameState
from core.voice import gremlin_quest_prompt
from quests.manager import QuestManager
from quests.rewards import apply_quest_reward
from quests.schema import QuestProgress


QUEST_ID = "literal_gremlins"
LEGACY_KEYS = ("gremlins", "gremlins_done", "cto_badge_unlocked")


class LiteralGremlinsQuest:
    def __init__(self, state: GameState, data: dict[str, Any], definition: dict[str, Any] | None = None) -> None:
        self.state = state
        self.data = data
        self.manager = QuestManager(state)
        self.definition = definition or load_quest_definition(QUEST_ID)

    def handle_event(self, event_type: str, payload: dict[str, Any]) -> dict | None:
        if event_type == "social":
            return self.handle_social(
                npc_id=str(payload.get("npc_id", "")),
                player_input=str(payload.get("player_input", "")),
                force_offer=bool(payload.get("force_offer", False)),
            )
        return None

    def handle_social(
        self,
        npc_id: str,
        player_input: str,
        force_offer: bool = False,
    ) -> dict | None:
        entrypoint = self._social_entrypoint()
        if self.definition["status"] != "enabled" or not entrypoint:
            return None
        if npc_id != entrypoint["npc_id"]:
            return None

        progress = self._progress()
        if progress and progress.status in {"completed", "failed"}:
            return None

        if progress and progress.status == "active":
            return self._advance(progress, player_input)

        if self._should_offer(player_input, force_offer):
            self._ensure_jason_relationship()
            reward_flags = {
                key: False
                for reward in self.definition["rewards"].values()
                for key in reward.get("flags", {})
            }
            self.manager.start(
                QUEST_ID,
                stage=self.definition["initial_stage"],
                flags=reward_flags,
                counters={"score": 0, "attempts": 0},
            )
            start_result = self.definition["start_result"]
            return {
                "outcome": start_result["outcome"],
                "flavor": start_result["flavor"],
                "scene": start_result["scene"],
                "npc_id": entrypoint["npc_id"],
            }

        return None

    def _progress(self) -> QuestProgress | None:
        progress = self.manager.get(QUEST_ID)
        if progress:
            return progress
        return self._migrate_legacy_progress()

    def _migrate_legacy_progress(self) -> QuestProgress | None:
        quests = self.state.player.quests
        legacy = quests.get("gremlins")
        legacy_done = bool(quests.get("gremlins_done"))
        if not isinstance(legacy, dict) and not legacy_done:
            return None

        legacy_stage = int(legacy.get("stage", 1)) if isinstance(legacy, dict) else 4
        score = int(legacy.get("score", 0)) if isinstance(legacy, dict) else 0
        completed = legacy_done or bool(legacy.get("completed")) if isinstance(legacy, dict) else legacy_done
        status = "completed" if completed else "active"
        stage = "completed" if completed else self._stage_id_for_prompt_stage(legacy_stage)
        cto_badge_unlocked = bool(quests.get("cto_badge_unlocked")) or "cto_badge" in self.state.player.unlocks

        progress = QuestProgress(
            quest_id=QUEST_ID,
            status=status,
            stage=stage,
            flags={"cto_badge_unlocked": cto_badge_unlocked},
            counters={"score": score, "attempts": 0},
        )
        self.manager.save(progress)
        self.manager.remove_legacy_keys(LEGACY_KEYS)
        return progress

    def _should_offer(self, player_input: str, force_offer: bool) -> bool:
        entrypoint = self._social_entrypoint()
        if not entrypoint:
            return False
        should_auto_offer = (
            bool(entrypoint.get("allow_empty_forced_offer", False))
            and force_offer
            and not str(player_input or "").strip()
        )
        should_keyword_offer = any(trigger in player_input.lower() for trigger in entrypoint.get("triggers", []))
        return should_auto_offer or should_keyword_offer

    def _advance(self, progress: QuestProgress, player_input: str) -> dict:
        stage = self._stage(progress.stage)
        stage_number = int(stage["prompt_stage"])
        progress.counters["attempts"] = progress.counters.get("attempts", 0) + 1

        prompt = gremlin_quest_prompt(
            stage_number,
            player_input,
            self.state.snapshot(),
            objective=str(stage["objective"]),
            success_cues=list(stage["success_cues"]),
            failure_cues=list(stage["failure_cues"]),
        )
        llm_result = call_llm_json(
            system_prompt=prompt,
            user_prompt=f"Player Action: {player_input}",
            temperature=0.2,
        )
        if not llm_result:
            llm_result = self._fallback_stage_eval(stage_number, player_input)

        success = bool(llm_result.get("success", False))
        if success:
            progress.counters["score"] = progress.counters.get("score", 0) + 1

        self._advance_stage(progress)

        if progress.stage in {"completed", "failed"}:
            return self._finish(progress, stage, llm_result, success)

        self.manager.save(progress)
        return {
            "outcome": "success" if success else "partial",
            "flavor": self._stage_result_flavor(stage, llm_result, success, progress.stage),
            "energy_delta": int(llm_result.get("energy_delta", -5)),
            "stress_delta": int(llm_result.get("stress_delta", 5)),
            "scene": self.definition["completion"]["active_scene"],
            "npc_id": "jason_it",
        }

    def _advance_stage(self, progress: QuestProgress) -> None:
        progress.stage = str(self._stage(progress.stage)["next_stage"])

    def _finish(
        self,
        progress: QuestProgress,
        stage: dict[str, Any],
        llm_result: dict,
        stage_success: bool,
    ) -> dict:
        score = progress.counters.get("score", 0)
        self._ensure_jason_relationship()
        completion = self.definition["completion"]
        if score >= completion["legendary_min_score"]:
            reward = self.definition["rewards"]["legendary"]
            scene = completion["success_scene"]
            outcome = "legendary"
            complete = True
        elif score >= completion["success_min_score"]:
            reward = self.definition["rewards"]["success"]
            scene = completion["success_scene"]
            outcome = "success"
            complete = True
        else:
            reward = self.definition["rewards"]["failure"]
            scene = completion["failure_scene"]
            outcome = "failed"
            complete = False

        apply_quest_reward(self.state, progress, reward)
        flavor = self._stage_result_flavor(stage, llm_result, stage_success, progress.stage)
        flavor = flavor + reward.get("flavor_append", "")
        if complete:
            progress.stage = "completed"
            self.manager.complete(progress)
        else:
            progress.stage = "failed"
            self.manager.fail(progress)
        return {
            "outcome": outcome,
            "flavor": flavor,
            "scene": scene,
            "npc_id": "jason_it",
        }

    def _fallback_stage_eval(self, stage: int, player_input: str) -> dict[str, Any]:
        stage_def = self._stage_by_prompt_stage(stage)
        cues = set(stage_def["success_cues"])
        text = str(player_input or "").lower()
        success = any(cue in text for cue in cues)

        if success:
            return {
                "success": True,
                "stage_complete": True,
                "flavor": stage_def["success_flavor"],
                "energy_delta": -6,
                "stress_delta": 2,
            }

        return {
            "success": False,
            "stage_complete": True,
            "flavor": stage_def["failure_flavor"],
            "energy_delta": -4,
            "stress_delta": 4,
        }

    def _stage_result_flavor(
        self,
        stage: dict[str, Any],
        llm_result: dict[str, Any],
        success: bool,
        next_stage: str,
    ) -> str:
        default_flavor = stage["success_flavor"] if success else stage["failure_flavor"]
        flavor = str(default_flavor).strip()
        if next_stage not in {"completed", "failed"}:
            flavor = f"{flavor}\n\n{self._stage(next_stage)['briefing']}"
        return flavor

    def _stage(self, stage_id: str) -> dict[str, Any]:
        stages = self.definition["stages"]
        if stage_id not in stages:
            raise ValueError(f"Unknown quest stage {stage_id!r} for {QUEST_ID}.")
        return stages[stage_id]

    def _stage_by_prompt_stage(self, prompt_stage: int) -> dict[str, Any]:
        for stage in self.definition["stages"].values():
            if int(stage["prompt_stage"]) == prompt_stage:
                return stage
        return self._stage(self.definition["initial_stage"])

    def _stage_id_for_prompt_stage(self, prompt_stage: int) -> str:
        for stage_id, stage in self.definition["stages"].items():
            if int(stage["prompt_stage"]) == prompt_stage:
                return stage_id
        return self.definition["initial_stage"]

    def _social_entrypoint(self) -> dict[str, Any] | None:
        return next(
            (entrypoint for entrypoint in self.definition["entrypoints"] if entrypoint.get("type") == "social"),
            None,
        )

    def _ensure_jason_relationship(self) -> None:
        if "jason_it" in self.state.player.relationships:
            return
        npc = next((entry for entry in self.data.get("npcs", []) if entry.get("id") == "jason_it"), None)
        if not npc:
            return
        self.state.init_relationship(
            npc_id="jason_it",
            name=npc.get("name", "Unknown"),
            role=npc.get("role", "Unknown"),
            pfp=npc.get("pfp"),
            trust=npc.get("base_trust", 50),
            rivalry=npc.get("base_rivalry", 0),
        )

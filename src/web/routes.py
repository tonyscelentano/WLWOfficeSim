import json
import logging
import os
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from core.state import AUTOSAVE_SLOT, SAVE_SLOTS, list_saves
from systems.onboarding import evaluate_interview, get_initial_question, get_next_question
from systems.pitch import evaluate_pitch
from web.http_utils import send_json, serve_file


@dataclass(frozen=True)
class RouteContext:
    session: Any
    static_dir: Path
    scenes_dir: Path
    pfps_dir: Path
    minigames_dir: Path
    log: logging.Logger


def handle_get(handler: BaseHTTPRequestHandler, path: str, ctx: RouteContext) -> bool:
    if path == "/":
        serve_file(handler, ctx.static_dir / "index.html")
        return True

    if path == "/api/state":
        _handle_state(handler, ctx)
        return True

    if path == "/api/stream":
        _handle_stream(handler, ctx)
        return True

    if path == "/api/saves":
        send_json(handler, {"saves": list_saves()})
        return True

    if path.startswith("/assets/scenes/"):
        serve_file(handler, ctx.scenes_dir / Path(path).name)
        return True

    if path.startswith("/assets/PFPs/"):
        serve_file(handler, ctx.pfps_dir / Path(path).name)
        return True

    if path.startswith("/static/"):
        serve_file(handler, ctx.static_dir / path.removeprefix("/static/"))
        return True

    if path.startswith("/minigames/"):
        _handle_minigame_file(handler, path, ctx)
        return True

    return False


def handle_post(handler: BaseHTTPRequestHandler, path: str, body: dict, ctx: RouteContext) -> bool:
    routes = {
        "/api/application/submit": _post_application_submit,
        "/api/onboarding/answer": _post_onboarding_answer,
        "/api/onboarding/confirm": _post_onboarding_confirm,
        "/api/action": _post_action,
        "/api/tutorial/finish": _post_tutorial_finish,
        "/api/pitch/evaluate": _post_pitch_evaluate,
        "/api/player/vitals": _post_player_vitals,
        "/api/config/nim-key": _post_config_nim_key,
        "/api/load": _post_load,
        "/api/logout": _post_logout,
    }

    if path in ("/api/new-career", "/api/new-game"):
        _post_new_career(handler, body, ctx)
        return True

    route = routes.get(path)
    if route is None:
        return False

    route(handler, body, ctx)
    return True


def _handle_state(handler: BaseHTTPRequestHandler, ctx: RouteContext) -> None:
    session = ctx.session
    with session.lock:
        phase = session.current_phase()
        if phase == "menu":
            payload = {
                "phase": "menu",
                "saves": list_saves(),
                "scene": "SCENE_HR_OFFICE",
            }
        elif phase == "game":
            payload = {
                "phase": "game",
                "slot": session.current_slot,
                "state": session.engine.state.snapshot(),
                "scene": "SCENE_DESK" if session.is_loaded_session else "SCENE_HR_OFFICE",
                "onboarding": session.onboarding_result,
                "is_load": session.is_loaded_session,
            }
        elif phase == "result":
            payload = {
                "phase": "result",
                "onboarding": session.onboarding_result,
                "scene": "SCENE_INTERVIEW_HIRED",
            }
        elif phase == "application":
            payload = {
                "phase": "application",
                "application": session.application_data,
                "scene": "SCENE_INTERVIEW",
            }
        else:
            payload = {
                "phase": "onboarding",
                "question": (
                    get_initial_question(session.application_data)
                    if not session.onboarding_transcript
                    else session.onboarding_transcript[-1]["content"]
                ),
                "turns": session.onboarding_turns,
                "scene": "SCENE_INTERVIEW",
            }

    send_json(handler, payload)


def _handle_stream(handler: BaseHTTPRequestHandler, ctx: RouteContext) -> None:
    session = ctx.session
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.end_headers()

    last_version = -1
    try:
        while True:
            with session.lock:
                if not session.session_active:
                    break
                current_version = session.engine.state.version
                if current_version != last_version:
                    phase = session.current_phase()
                    payload = {
                        "phase": phase,
                        "state": session.engine.state.snapshot() if phase == "game" else None,
                    }
                    message = f"data: {json.dumps(payload)}\n\n"
                    handler.wfile.write(message.encode("utf-8"))
                    handler.wfile.flush()
                    last_version = current_version
            time.sleep(0.5)
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        ctx.log.info("SSE client disconnected.")


def _handle_minigame_file(handler: BaseHTTPRequestHandler, path: str, ctx: RouteContext) -> None:
    rel = path.removeprefix("/minigames/")
    target = ctx.minigames_dir / rel / "index.html" if not rel or rel.endswith("/") else ctx.minigames_dir / rel

    try:
        target = target.resolve(strict=False)
        target.relative_to(ctx.minigames_dir.resolve())
    except (ValueError, OSError):
        handler.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
        return

    serve_file(handler, target)


def _post_application_submit(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    name = (body.get("name") or "").strip()
    age = (body.get("age") or "").strip()
    work_history = (body.get("work_history") or "").strip()
    preferred_role = (body.get("preferred_role") or "").strip()
    if not name:
        send_json(handler, {"error": "Missing name"}, status=400)
        return

    with session.lock:
        if not session.session_active:
            send_json(handler, {"error": "No active session — start a new career first"}, status=409)
            return
        if session.onboarding_done:
            send_json(handler, {"error": "Game already started"}, status=409)
            return
        session.application_data = {
            "name": name[:80],
            "age": age[:20],
            "work_history": work_history[:500],
            "preferred_role": preferred_role[:120],
        }
        session.application_done = True
        if not session.onboarding_transcript:
            session.onboarding_transcript = [{"role": "interviewer", "content": get_initial_question(session.application_data)}]
        send_json(
            handler,
            {
                "phase": "onboarding",
                "question": session.onboarding_transcript[0]["content"],
                "turns": session.onboarding_turns,
                "scene": "SCENE_INTERVIEW",
            },
        )


def _post_onboarding_answer(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    answer = (body.get("answer") or "").strip()
    if not answer:
        send_json(handler, {"error": "Missing answer"}, status=400)
        return

    with session.lock:
        if not session.application_done:
            send_json(handler, {"error": "Application not submitted"}, status=409)
            return
        if session.onboarding_done:
            send_json(handler, {"error": "Onboarding already completed"}, status=409)
            return

        session.onboarding_transcript.append({"role": "user", "content": answer})
        session.onboarding_turns += 1

        if session.onboarding_turns < 3:
            next_q = get_next_question(session.onboarding_transcript, session.application_data)
            session.onboarding_transcript.append({"role": "interviewer", "content": next_q})
            send_json(handler, {"phase": "onboarding", "question": next_q, "turns": session.onboarding_turns})
            return

        result = evaluate_interview(session.onboarding_transcript, session.application_data)
        session.engine.new_game(session.application_data.get("name") or "Player")
        player = session.engine.state.player
        player.department = f"{result.get('pillar', 'technical')}.{result.get('path', 'middle')}.{result.get('cluster', 'backend')}"
        player.title = result.get("role", "Junior Backend Dev")
        for skill, value in result.get("starting_skills", {}).items():
            player.skills[skill] = value
        session.onboarding_done = True
        session.onboarding_result = dict(result)

        try:
            session.engine.state.save_slot(session.current_slot, meta={
                "application": dict(session.application_data),
                "onboarding_result": dict(session.onboarding_result),
            })
        except Exception:
            ctx.log.exception("Initial autosave after onboarding failed.")

        send_json(
            handler,
            {
                "phase": "result",
                "onboarding": session.onboarding_result,
                "scene": "SCENE_INTERVIEW_HIRED",
            },
        )


def _post_onboarding_confirm(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    with session.lock:
        if not session.onboarding_done:
            send_json(handler, {"error": "Onboarding not complete"}, status=409)
            return
        session.result_viewed = True
        send_json(handler, {
            "phase": "game",
            "state": session.engine.state.snapshot(),
            "scene": "SCENE_HR_OFFICE",
        })


def _post_action(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    verb = (body.get("verb") or "").strip()
    player_input = (body.get("input") or "").strip()
    npc_id = (body.get("npc_id") or "").strip()
    if not verb:
        send_json(handler, {"error": "Missing verb"}, status=400)
        return

    with session.lock:
        if not session.onboarding_done:
            send_json(handler, {"error": "Onboarding not complete"}, status=409)
            return
        kwargs: dict[str, str] = {"player_input": player_input}
        if verb == "socialize":
            kwargs["npc_id"] = npc_id
        result = session.engine.handle_action(verb, **kwargs)
        send_json(handler, {"result": result, "state": session.engine.state.snapshot()})


def _post_tutorial_finish(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    with session.lock:
        if not session.session_active or not session.onboarding_done:
            send_json(handler, {"error": "No active game session"}, status=409)
            return
        session.engine.state.player.tutorial_done = True
        try:
            session.engine.state.save_slot(session.current_slot)
        except Exception:
            ctx.log.exception("Failed to save tutorial_done status.")
        send_json(handler, {"ok": True, "state": session.engine.state.snapshot()})


def _post_pitch_evaluate(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    with session.lock:
        if not session.session_active:
            send_json(handler, {"error": "No active session"}, status=409)
            return

        if session.engine.state.is_burnt_out():
            send_json(handler, {"error": "HR BLOCK: Burnout Protocol active. Slide deck authorization revoked."}, status=403)
            return

        result = evaluate_pitch(body)

        if result.get("outcome") == "failure":
            session.engine.state.player.pitch_fail_count += 1
            if session.engine.state.player.pitch_fail_count >= 2:
                session.engine.state.add_hr_warning(
                    "Performance Audit: Repeated failure to secure pitch approvals. Resource waste flagged."
                )
        else:
            session.engine.state.player.pitch_fail_count = 0

        send_json(handler, {"result": result})


def _post_player_vitals(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    with session.lock:
        if not session.session_active:
            send_json(handler, {"error": "No active session"}, status=409)
            return

        allowed = {}
        for key in ("energy", "stress"):
            if key in body:
                try:
                    delta = int(body[key])
                    allowed[key] = max(-50, min(50, delta))
                except (ValueError, TypeError):
                    pass
        applied = session.engine.state.apply_delta(allowed)

        try:
            session.engine.state.save_slot(session.current_slot)
        except Exception:
            ctx.log.exception("Autosave failed in /api/player/vitals")

        send_json(handler, {
            "applied": applied,
            "state": session.engine.state.snapshot(),
        })


def _post_config_nim_key(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    raw_key = body.get("api_key")
    api_key = str(raw_key or "").strip()

    if api_key:
        if not api_key.startswith("nvapi-"):
            send_json(handler, {"error": "NVIDIA NIM API key should start with nvapi-"}, status=400)
            return
        os.environ["NVIDIA_API_KEY"] = api_key
        os.environ["NIM_API_KEY"] = api_key
        send_json(handler, {"ok": True, "configured": True})
        return

    os.environ.pop("NVIDIA_API_KEY", None)
    os.environ.pop("NIM_API_KEY", None)
    send_json(handler, {"ok": True, "configured": False})


def _post_new_career(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    session.reset()
    with session.lock:
        session.session_active = True
    send_json(
        handler,
        {
            "phase": "application",
            "turns": 0,
            "scene": "SCENE_INTERVIEW",
        },
    )


def _post_load(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    try:
        slot = int(body.get("slot", AUTOSAVE_SLOT))
    except (TypeError, ValueError):
        send_json(handler, {"error": "Invalid slot"}, status=400)
        return
    if slot not in SAVE_SLOTS:
        send_json(handler, {"error": f"Unknown slot {slot}"}, status=400)
        return

    with session.lock:
        try:
            meta = session.engine.load_game(slot=slot)
        except FileNotFoundError:
            send_json(handler, {"error": f"Slot {slot} is empty"}, status=404)
            return
        except ValueError as exc:
            send_json(handler, {"error": str(exc)}, status=409)
            return
        except Exception:
            ctx.log.exception("Load failed for slot %d", slot)
            send_json(handler, {"error": "Load failed — see server log"}, status=500)
            return

        session.application_data = dict(meta.get("application") or {})
        session.onboarding_result = dict(meta.get("onboarding_result") or {})
        session.onboarding_transcript = []
        session.onboarding_turns = 0
        session.application_done = True
        session.onboarding_done = True
        session.result_viewed = True
        session.session_active = True
        session.current_slot = slot
        session.is_loaded_session = True

    send_json(handler, {
        "phase": "game",
        "slot": slot,
        "state": session.engine.state.snapshot(),
        "scene": "SCENE_DESK",
    })


def _post_logout(handler: BaseHTTPRequestHandler, body: dict, ctx: RouteContext) -> None:
    session = ctx.session
    with session.lock:
        if session.session_active and session.onboarding_done and session.engine._initialized:
            try:
                session.engine.state.save_slot(session.current_slot, meta={
                    "application": dict(session.application_data),
                    "onboarding_result": dict(session.onboarding_result),
                })
            except Exception:
                ctx.log.exception("Save-on-logout failed for slot %d", session.current_slot)

    session.reset()

    send_json(handler, {
        "phase": "menu",
        "saves": list_saves(),
        "scene": "SCENE_HR_OFFICE",
    })

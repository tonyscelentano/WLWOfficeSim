from pathlib import Path
from dotenv import load_dotenv

# CRITICAL: Load environment variables BEFORE any project imports
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

import json
import logging
import os
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.engine import Engine
from core.state import AUTOSAVE_SLOT
from web.http_utils import read_json, send_json
from web.routes import RouteContext, handle_get, handle_post


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("web.server")

ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
SCENES_DIR = ROOT / "assets" / "Scenes"
PFPS_DIR = ROOT / "assets" / "PFPs"
MINIGAMES_DIR = ROOT / "TaskMinigames"

class SessionManager:
    """
    Thread-safe container for game session state.
    Replaces unsafe global variables to prevent race conditions.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.engine = Engine()
        self.application_data: dict[str, str] = {}
        self.application_done = False
        self.onboarding_transcript: list[dict[str, str]] = []
        self.onboarding_turns = 0
        self.onboarding_done = False
        self.onboarding_result: dict[str, Any] = {}
        self.result_viewed = False
        self.session_active = False
        self.current_slot: int = AUTOSAVE_SLOT
        self.is_loaded_session = False

    def reset(self):
        """Wipe session state back to a fresh main-menu state."""
        with self.lock:
            self.application_data = {}
            self.application_done = False
            self.onboarding_transcript = []
            self.onboarding_turns = 0
            self.onboarding_done = False
            self.onboarding_result = {}
            self.result_viewed = False
            self.session_active = False
            self.current_slot = AUTOSAVE_SLOT
            self.is_loaded_session = False
            # Drop the engine's gameplay state but keep the singleton
            self.engine.reset_career_bus()
            self.engine.state = self.engine.state.__class__()
            self.engine._initialized = False

    def current_phase(self) -> str:
        """Resolve which phase the client should render."""
        if not self.session_active:
            return "menu"
        if self.onboarding_done:
            return "game" if self.result_viewed else "result"
        if not self.application_done:
            return "application"
        return "onboarding"

session = SessionManager()
routes = RouteContext(
    session=session,
    static_dir=STATIC_DIR,
    scenes_dir=SCENES_DIR,
    pfps_dir=PFPS_DIR,
    minigames_dir=MINIGAMES_DIR,
    log=log,
)

def run_tick_loop():
    """Background daemon thread to drive the engine's real-time tick loop."""
    log.info("Starting background engine tick loop.")
    while True:
        try:
            with session.lock:
                if session.session_active and session.onboarding_done and session.engine._initialized:
                    session.engine.tick()
        except Exception:
            log.exception("Error in background tick loop.")
        time.sleep(60)

# Start tick loop immediately in a daemon thread
threading.Thread(target=run_tick_loop, daemon=True).start()


class OfficeSimHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if handle_get(self, path, routes):
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            body = read_json(self)
        except json.JSONDecodeError:
            send_json(self, {"error": "Invalid JSON body"}, status=400)
            return

        if handle_post(self, path, body, routes):
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args) -> None:
        log.info("%s - %s", self.address_string(), format % args)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    env_host = (os.environ.get("HOST") or host).strip() or host
    env_port_raw = (os.environ.get("PORT") or str(port)).strip()
    try:
        env_port = int(env_port_raw)
    except ValueError as exc:
        raise ValueError(f"Invalid PORT value {env_port_raw!r}; expected integer.") from exc

    try:
        server = ThreadingHTTPServer((env_host, env_port), OfficeSimHandler)
    except OSError as exc:
        raise RuntimeError(
            f"OfficeSim failed to bind http://{env_host}:{env_port}. "
            f"This is usually a port conflict or local socket/network stack issue. "
            f"Original error: {exc}"
        ) from exc

    log.info("OfficeSim web server listening on http://%s:%d", env_host, env_port)
    server.serve_forever()


if __name__ == "__main__":
    run()

from __future__ import annotations

from core.bus import bus
from core.state import GameState


def publish_presence_trait(state: GameState) -> None:
    log_data = state.player.presence_log
    if len(log_data) < 3:
        return

    recent = log_data[-5:]
    avg_minutes = sum(entry["minutes_active"] for entry in recent) / len(recent)

    if avg_minutes >= 720:
        trait = "never_leaves"
    elif avg_minutes >= 540:
        trait = "overachiever"
    elif avg_minutes >= 420:
        trait = "solid_nine_to_five"
    elif avg_minutes < 60:
        trait = "ghost"
    else:
        trait = None

    if trait:
        bus.publish("presence_trait_updated", {
            "trait": trait,
            "avg_minutes": round(avg_minutes),
        })

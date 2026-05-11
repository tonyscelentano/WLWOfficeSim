from __future__ import annotations

import logging


def apply_action_scene(
    result: dict,
    verb: str,
    stress: int,
    log: logging.Logger,
) -> None:
    scene_img = "SCENE_DESK"

    if verb == "work":
        if result.get("outcome") in ["success", "legendary"]:
            scene_img = "SCENE_DESK_SUCCESS"
        elif result.get("outcome") == "dumpster_fire":
            scene_img = "SCENE_DESK_FAIL"
            if stress > 85:
                scene_img = "SCENE_RACKS_ON_FIRE"

    elif verb == "socialize":
        if result.get("scene_override"):
            log.info("Social Scene Override: %s", result["scene_override"])
            result["scene"] = result["scene_override"]
        elif not result.get("scene"):
            scene_img = "SCENE_WATERCOOLER"
            result["scene"] = scene_img

    elif verb == "recover":
        result["scene"] = "SCENE_RECOVER"

    elif verb == "slack":
        result["scene"] = "SCENE_SLACKING"

    elif verb == "visit_it":
        if not result.get("scene"):
            result["scene"] = "SCENE_IT_BASEMENT"

    elif verb == "learn":
        scene_img = "SCENE_DESK"

    if not result.get("scene"):
        result["scene"] = scene_img

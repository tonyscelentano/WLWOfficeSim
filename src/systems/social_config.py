"""
social_config.py — Shared knobs for coworker social systems.

This is intentionally data-like. Keep policy constants here so feature modules
stay small and easy for later agents to extend.
"""
from __future__ import annotations

ARCHETYPE_PRIORITIES = {
    "chaotic_genius": ("technical_credibility", 7),
    "political": ("client_cover", 8),
    "operator": ("process_leverage", 6),
    "visionary": ("taste_and_clarity", 5),
    "gossip": ("shadow_intel", 4),
    "mentor": ("career_guidance", 6),
}

CLUSTER_ADJACENCY = {
    "backend": {"architecture", "devops", "product"},
    "architecture": {"backend", "devops", "executive"},
    "frontend": {"design", "product", "mobile"},
    "mobile": {"frontend", "design"},
    "design": {"frontend", "product", "copy"},
    "copy": {"design", "sales", "csm"},
    "product": {"design", "backend", "scrum", "csm"},
    "scrum": {"product", "backend", "design", "csm"},
    "csm": {"product", "sales", "executive"},
    "sales": {"csm", "executive", "legal"},
    "hr": {"culture", "executive"},
    "culture": {"hr", "executive"},
    "executive": {"board", "architecture", "sales", "csm", "hr", "accounting"},
    "board": {"executive", "legal"},
    "accounting": {"executive", "legal", "data"},
    "legal": {"executive", "accounting", "sales"},
    "devops": {"backend", "architecture", "data"},
    "data": {"devops", "accounting", "legal"},
}

PRESENCE_STYLE_MODIFIERS = {
    "never_leaves": {"mentor": 1, "operator": 1, "gossip": -1},
    "overachiever": {"chaotic_genius": 1, "political": 1},
    "solid_nine_to_five": {"operator": 1, "mentor": 1},
    "ghost": {"gossip": -1, "political": -1, "mentor": -1},
}

SOCIAL_ACTION_COSTS = {
    "small_talk": {"energy": 4, "risk": 1},
    "ask_for_favor": {"energy": 8, "risk": 4},
    "seek_mentorship": {"energy": 6, "risk": 2},
    "gather_rumor": {"energy": 5, "risk": 5},
    "relationship_maintenance": {"energy": 3, "risk": 0},
}

SOCIAL_ACTIONS = set(SOCIAL_ACTION_COSTS)

TRUST_TIERS = {
    "sponsor": 80,
    "ally": 60,
    "warm": 40,
    "known": 20,
}

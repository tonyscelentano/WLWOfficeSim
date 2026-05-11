from __future__ import annotations

import random
from typing import Any, Iterable, Mapping

WATERCOOLER_ALIASES = {
    'alex_manager': 'alex_lead',
    'lead': 'alex_lead',
    'middlemanagement': 'alex_lead',
    'middle_management': 'alex_lead',
    'sam': 'sam_coworker',
    'coworker': 'sam_coworker',
    'good_news_guy': 'sam_coworker',
    'root': 'root_devops_cat',
    'patch': 'root_devops_cat',
    'devops': 'root_devops_cat',
    'cat': 'root_devops_cat',
    'diane': 'diane_gossip',
    'gossip': 'diane_gossip',
    'gossipgirls': 'diane_gossip',
    'nina': 'nina_hr',
    'hr': 'nina_hr',
    'hr_partner': 'nina_hr',
    'iris': 'iris_it',
    'it': 'iris_it',
    'random_dev': 'iris_it',
    'robo': 'robo_janitor',
    'janitor': 'robo_janitor',
    'cleanbot': 'robo_janitor',
    'tom': 'tom_finance',
    'finance': 'tom_finance',
    'chen': 'chen_ux',
    'ux': 'chen_ux',
    'pam': 'pam_reception',
    'receptionist': 'pam_reception',
    'carlos': 'carlos_investor',
    'investor': 'carlos_investor',
    'hr_lady': 'hr_lady',
    'matt': 'matt_sales',
    'sales': 'matt_sales',
    'tony': 'tony_it',
    'shadow_it': 'tony_it',
    'timothy': 'timothy_intern',
    'intern': 'timothy_intern',
    'hany': 'hany_pm',
    'pm': 'hany_pm',
    'keith': 'keith_bro',
    'brogrammer': 'keith_bro',
    'todd': 'investor_todd',
    'todd_investor': 'investor_todd',
    'angel': 'investor_todd',
}

HIGH_STRESS_CONTEXT = 'root_devops_cat'


def _all_npc_ids(npcs: Any) -> list[str]:
    npc_list = npcs.values() if isinstance(npcs, Mapping) else npcs
    return [
        str(npc.get('id', '')).strip()
        for npc in npc_list
        if isinstance(npc, Mapping) and npc.get('id')
    ]


def _available_watercooler_ids(npcs: Any) -> list[str]:
    # Handle dict of dicts or list of dicts
    npc_list = npcs.values() if isinstance(npcs, Mapping) else npcs
    return [
        str(npc.get('id', '')).strip() 
        for npc in npc_list 
        if isinstance(npc, Mapping)
        and npc.get('watercooler_scene')
        and npc.get('watercooler_seed')
        and npc.get('watercooler_pool', True)  # False = excluded from random pool
    ]


def resolve_watercooler_npc_id(
    requested_npc_id: str | None,
    npcs: Iterable[Mapping[str, Any]],
    stress: int = 0,
    rng: random.Random | None = None,
    discovered_npcs: set[str] | None = None,
    lock_requested_npc: bool = False,
) -> str:
    npc_list = npcs.values() if isinstance(npcs, Mapping) else npcs
    all_ids = _all_npc_ids(npc_list)
    requested = str(requested_npc_id or '').strip().lower()
    normalized = requested.replace('-', '_')

    if lock_requested_npc and normalized:
        if normalized in all_ids:
            return normalized
        alias = WATERCOOLER_ALIASES.get(normalized)
        if alias and alias in all_ids:
            return alias
        return normalized

    available = _available_watercooler_ids(npc_list)
    if not available:
        return str(requested_npc_id or '').strip()

    if stress >= 85 and HIGH_STRESS_CONTEXT in available:
        return HIGH_STRESS_CONTEXT

    if normalized in available:
        return normalized
    if normalized in WATERCOOLER_ALIASES and WATERCOOLER_ALIASES[normalized] in available:
        return WATERCOOLER_ALIASES[normalized]

    chooser = rng or random

    if discovered_npcs is not None:
        undiscovered = [n for n in available if n not in discovered_npcs]
        if undiscovered and chooser.random() < 0.8:
            return chooser.choice(undiscovered)

    return chooser.choice(available)


def watercooler_context_for_npc(
    npc_id: str, 
    npcs: Iterable[Mapping[str, Any]],
    last_outcome: str | None = None, 
    player_input: str = '',
    lock_requested_npc: bool = False,
) -> dict[str, str]:
    npc_list = npcs.values() if isinstance(npcs, Mapping) else npcs
    npc = next((n for n in npc_list if isinstance(n, Mapping) and n.get('id') == npc_id), None)
    if not npc:
        if lock_requested_npc:
            return {
                'npc_id': npc_id,
                'scene': '',
                'seed': player_input or 'You look around for someone who never shows up.',
            }
    if npc and not npc.get('watercooler_scene') and lock_requested_npc:
        return {
            'npc_id': npc_id,
            'scene': '',
            'seed': npc.get('watercooler_seed', 'Someone is looking at the water cooler.'),
        }
    if not npc or not npc.get('watercooler_scene'):
        # Fallback
        npc = next((n for n in npc_list if isinstance(n, Mapping) and n.get('id') == 'sam_coworker'), None)
        if not npc:
            # Absolute fallback
            return {
                'npc_id': 'sam_coworker',
                'scene': 'Watercooler_Personnel_Generic-Coworker.jpeg',
                'seed': 'Sam is telling a meandering story about his weekend that somehow transitioned into expense report complaints.',
            }
            
    scene = npc.get('watercooler_scene')
    seed = npc.get('watercooler_seed', 'Someone is looking at the water cooler.')
    
    if npc_id == 'hany_pm':
        flirt_keywords = ['wink', 'flirt', 'beautiful', 'stunning', 'date', 'coffee', 'smile', 'cute', 'night', 'shift', 'closet', 'hot', 'sexy']
        is_flirting = any(k in player_input.lower() for k in flirt_keywords)
        if is_flirting or last_outcome == 'legendary':
            scene = 'Watercooler_Personnel_Generic-HanyAmused.jpeg'

    return {
        'npc_id': npc_id if npc else 'sam_coworker',
        'scene': scene,
        'seed': seed,
    }


def choose_watercooler_context(
    requested_npc_id: str | None,
    npcs: Iterable[Mapping[str, Any]],
    stress: int = 0,
    rng: random.Random | None = None,
    last_outcome: str | None = None,
    player_input: str = '',
    discovered_npcs: set[str] | None = None,
    lock_requested_npc: bool = False,
) -> dict[str, str]:
    npc_id = resolve_watercooler_npc_id(
        requested_npc_id,
        npcs,
        stress,
        rng,
        discovered_npcs,
        lock_requested_npc=lock_requested_npc,
    )
    return watercooler_context_for_npc(
        npc_id,
        npcs,
        last_outcome,
        player_input,
        lock_requested_npc=lock_requested_npc,
    )

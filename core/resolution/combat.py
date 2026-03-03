from __future__ import annotations

from typing import List, Tuple

from core.actions import Action
from core.enums import EventType
from core.events import Event, create_event
from core.states.session import (
    GameSessionState,
    find_enemy_by_instance_id,
    find_player_by_instance_id,
)


def _normalize_target_ids(raw: object) -> Tuple[List[str], str]:
    if isinstance(raw, str):
        return [raw], ""
    if isinstance(raw, list):
        return [str(value) for value in raw], ""
    return [], "Invalid target_instance_ids"


def resolve_attack_action(session: GameSessionState, encounter, action: Action) -> List[Event]:
    target_ids, target_error = _normalize_target_ids(action.parameters.get("target_instance_ids", []))
    if target_error:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": [target_error]})]
    if not target_ids:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Missing targets"]})]

    actor_player = find_player_by_instance_id(session, action.actor_instance_id)
    actor_enemy = find_enemy_by_instance_id(encounter, action.actor_instance_id)
    if actor_player is None and actor_enemy is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Actor not found"]})]

    events: List[Event] = [
        create_event(
            EventType.ATTACK_DECLARED,
            "attack_declared",
            {"actor_instance_id": action.actor_instance_id, "attack_id": action.parameters.get("attack_id", "")},
        )
    ]

    for target_id in target_ids:
        target_player = find_player_by_instance_id(session, target_id)
        target_enemy = find_enemy_by_instance_id(encounter, target_id)
        target = target_player or target_enemy
        if target is None:
            events.append(
                create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": [f"Unknown target '{target_id}'"]})
            )
            continue

        damage = 1
        target.hp = max(0, target.hp - damage)
        events.append(create_event(EventType.ATTACK_HIT, "attack_hit", {"target_instance_id": target_id}))
        events.append(create_event(EventType.DAMAGE_APPLIED, "damage_applied", {"target_instance_id": target_id, "amount": damage}))
        events.append(create_event(EventType.HP_UPDATED, "hp_updated", {"target_instance_id": target_id, "hp": target.hp}))
        if target.hp == 0:
            events.append(create_event(EventType.DEATH, "death", {"target_instance_id": target_id}))

    return events


def resolve_cast_spell_action(session: GameSessionState, encounter, action: Action) -> List[Event]:
    target_ids, target_error = _normalize_target_ids(action.parameters.get("target_instance_ids", []))
    if target_error:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": [target_error]})]

    spell_id = str(action.parameters.get("spell_id", ""))
    is_heal = "heal" in spell_id.lower()
    events: List[Event] = [
        create_event(EventType.SPELL_CAST, "spell_cast", {"spell_id": spell_id, "actor_instance_id": action.actor_instance_id})
    ]

    for target_id in target_ids:
        target_player = find_player_by_instance_id(session, target_id)
        target_enemy = find_enemy_by_instance_id(encounter, target_id)
        target = target_player or target_enemy
        if target is None:
            events.append(
                create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": [f"Unknown target '{target_id}'"]})
            )
            continue

        if is_heal:
            amount = 1
            target.hp = min(target.max_hp, target.hp + amount)
            events.append(create_event(EventType.HEALING_APPLIED, "healing_applied", {"target_instance_id": target_id, "amount": amount}))
            events.append(create_event(EventType.HP_UPDATED, "hp_updated", {"target_instance_id": target_id, "hp": target.hp}))
        else:
            amount = 1
            target.hp = max(0, target.hp - amount)
            events.append(create_event(EventType.DAMAGE_APPLIED, "damage_applied", {"target_instance_id": target_id, "amount": amount}))
            events.append(create_event(EventType.HP_UPDATED, "hp_updated", {"target_instance_id": target_id, "hp": target.hp}))
            if target.hp == 0:
                events.append(create_event(EventType.DEATH, "death", {"target_instance_id": target_id}))

    return events

from __future__ import annotations

from typing import Any
from typing import List

from core.enums import ControlType, EventType, StatusEffectType
from core.events import Event, create_event
from core.states.session import (
    GameSessionState,
    find_enemy_by_instance_id,
    find_player_by_instance_id,
    get_active_encounter,
)


def _effect_type(effect: Any) -> StatusEffectType | None:
    status_effect = getattr(effect, "status_effect", None)
    if status_effect is None:
        return None
    effect_type = getattr(status_effect, "type", None)
    if isinstance(effect_type, StatusEffectType):
        return effect_type
    try:
        return StatusEffectType(str(effect_type))
    except (TypeError, ValueError):
        return None


def _control_type(effect: Any) -> ControlType | None:
    status_effect = getattr(effect, "status_effect", None)
    if status_effect is None:
        return None
    parameters = getattr(status_effect, "parameters", {})
    raw_value = parameters.get("control_type") if isinstance(parameters, dict) else None
    if raw_value is None:
        return None
    try:
        return ControlType(str(raw_value))
    except ValueError:
        return None


def _effect_value(effect: Any) -> int:
    status_effect = getattr(effect, "status_effect", None)
    if status_effect is None:
        return 0
    parameters = getattr(status_effect, "parameters", {})
    raw_value = parameters.get("value", 0) if isinstance(parameters, dict) else 0
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return 0


def _active_control_types(actor) -> List[ControlType]:
    controls: List[ControlType] = []
    for effect in actor.active_status_effects:
        if _effect_type(effect) != StatusEffectType.CONTROL:
            continue
        control_type = _control_type(effect)
        if control_type is not None:
            controls.append(control_type)
    return controls


def is_entity_stunned(actor) -> bool:
    return ControlType.STUNNED in _active_control_types(actor)


def is_entity_silenced(actor) -> bool:
    return ControlType.SILENCED in _active_control_types(actor)


def is_entity_asleep(actor) -> bool:
    return ControlType.ASLEEP in _active_control_types(actor)


def is_entity_restrained(actor) -> bool:
    return ControlType.RESTRAINED in _active_control_types(actor)


def remove_negative_status_effects_from_actor(actor, actor_instance_id: str) -> List[Event]:
    negative_types = {
        StatusEffectType.VULNERABLE,
        StatusEffectType.CONTROL,
        StatusEffectType.DOT,
    }
    kept_effects = []
    events: List[Event] = []
    for effect in actor.active_status_effects:
        if _effect_type(effect) not in negative_types:
            kept_effects.append(effect)
            continue
        events.append(
            create_event(
                EventType.STATUS_EFFECT_REMOVED,
                "status_effect_removed",
                {
                    "actor_instance_id": actor_instance_id,
                    "status_effect_id": effect.id,
                },
            )
        )
    actor.active_status_effects = kept_effects
    return events


def tick_status_effects_for_actor(session: GameSessionState, actor_instance_id: str) -> List[Event]:
    target_player = find_player_by_instance_id(session, actor_instance_id)
    encounter = get_active_encounter(session)
    target_enemy = find_enemy_by_instance_id(encounter, actor_instance_id) if encounter is not None else None
    actor = target_player or target_enemy
    if actor is None:
        return []

    events: List[Event] = []
    remaining = []
    for effect in actor.active_status_effects:
        effect_type = _effect_type(effect)
        if effect_type == StatusEffectType.DOT:
            value = max(0, _effect_value(effect))
            actor.hp = max(0, actor.hp - value)
            events.append(
                create_event(
                    EventType.DAMAGE_APPLIED,
                    "damage_applied",
                    {
                        "target_instance_id": actor_instance_id,
                        "amount": value,
                        "reason": "status_effect_tick",
                        "status_effect_id": effect.id,
                    },
                )
            )
            events.append(
                create_event(
                    EventType.HP_UPDATED,
                    "hp_updated",
                    {
                        "target_instance_id": actor_instance_id,
                        "hp": actor.hp,
                    },
                )
            )
            if actor.hp == 0:
                events.append(create_event(EventType.DEATH, "death", {"target_instance_id": actor_instance_id}))

        if effect_type == StatusEffectType.HOT:
            value = max(0, _effect_value(effect))
            actor.hp = min(actor.max_hp, actor.hp + value)
            events.append(
                create_event(
                    EventType.HEALING_APPLIED,
                    "healing_applied",
                    {
                        "target_instance_id": actor_instance_id,
                        "amount": value,
                        "reason": "status_effect_tick",
                        "status_effect_id": effect.id,
                    },
                )
            )
            events.append(
                create_event(
                    EventType.HP_UPDATED,
                    "hp_updated",
                    {
                        "target_instance_id": actor_instance_id,
                        "hp": actor.hp,
                    },
                )
            )

        effect.duration -= 1
        events.append(
            create_event(
                EventType.STATUS_EFFECT_TICKED,
                "status_effect_ticked",
                {
                    "actor_instance_id": actor_instance_id,
                    "status_effect_id": effect.id,
                    "duration": effect.duration,
                },
            )
        )
        if effect.duration <= 0:
            events.append(
                create_event(
                    EventType.STATUS_EFFECT_REMOVED,
                    "status_effect_removed",
                    {
                        "actor_instance_id": actor_instance_id,
                        "status_effect_id": effect.id,
                    },
                )
            )
            continue
        remaining.append(effect)
    actor.active_status_effects = remaining
    return events

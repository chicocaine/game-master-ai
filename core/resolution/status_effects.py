from __future__ import annotations

import math
from typing import Any
from typing import List

from core.enums import ControlType, DamageType, EventType, StatusEffectType
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


def _effect_damage_type(effect: Any) -> DamageType:
    status_effect = getattr(effect, "status_effect", None)
    if status_effect is None:
        return DamageType.FORCE
    parameters = getattr(status_effect, "parameters", {})
    raw_value = parameters.get("damage_type") if isinstance(parameters, dict) else None
    if raw_value is None:
        return DamageType.FORCE
    try:
        return DamageType(str(raw_value))
    except (TypeError, ValueError):
        return DamageType.FORCE


def _calculate_damage_multiplier(
    damage_type: DamageType,
    immunities: List[DamageType],
    resistances: List[DamageType],
    vulnerabilities: List[DamageType],
) -> float:
    if damage_type in immunities:
        return 0.0

    has_resistance = damage_type in resistances
    has_vulnerability = damage_type in vulnerabilities

    if has_resistance and has_vulnerability:
        return 1.0
    if has_resistance:
        return 0.5
    if has_vulnerability:
        return 2.0
    return 1.0


def _active_control_types(actor) -> List[ControlType]:
    controls: List[ControlType] = []
    for effect in actor.active_status_effects:
        if _effect_type(effect) != StatusEffectType.CONTROL:
            continue
        control_type = _control_type(effect)
        if control_type is not None:
            controls.append(control_type)
    return controls


def _apply_modifier_effect_to_actor(actor, effect: Any) -> None:
    effect_type = _effect_type(effect)
    value = _effect_value(effect)

    if effect_type == StatusEffectType.ACMOD:
        actor.AC = max(0, actor.AC + value)
        return

    if effect_type == StatusEffectType.ATKMOD:
        actor.attack_modifier_bonus = actor.attack_modifier_bonus + value


def _remove_modifier_effect_from_actor(actor, effect: Any) -> None:
    effect_type = _effect_type(effect)
    value = _effect_value(effect)

    if effect_type == StatusEffectType.ACMOD:
        actor.AC = max(0, actor.AC - value)
        return

    if effect_type == StatusEffectType.ATKMOD:
        actor.attack_modifier_bonus = actor.attack_modifier_bonus - value


def remove_status_effect_from_actor(actor, actor_instance_id: str, effect: Any) -> Event:
    _remove_modifier_effect_from_actor(actor, effect)
    return create_event(
        EventType.STATUS_EFFECT_REMOVED,
        "status_effect_removed",
        {
            "actor_instance_id": actor_instance_id,
            "status_effect_id": effect.id,
        },
    )


def apply_status_effect_to_actor(actor, actor_instance_id: str, effect: Any) -> List[Event]:
    events: List[Event] = []
    effect_type = _effect_type(effect)
    overwrite_types = {StatusEffectType.ACMOD, StatusEffectType.ATKMOD}

    if effect_type in overwrite_types:
        kept_effects = []
        for active_effect in actor.active_status_effects:
            if _effect_type(active_effect) != effect_type:
                kept_effects.append(active_effect)
                continue
            events.append(remove_status_effect_from_actor(actor, actor_instance_id, active_effect))
        actor.active_status_effects = kept_effects

    actor.active_status_effects.append(effect)
    _apply_modifier_effect_to_actor(actor, effect)
    events.append(
        create_event(
            EventType.STATUS_EFFECT_APPLIED,
            "status_effect_applied",
            {
                "target_instance_id": actor_instance_id,
                "status_effect_id": effect.id,
                "duration": effect.duration,
            },
        )
    )
    return events


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
        events.append(remove_status_effect_from_actor(actor, actor_instance_id, effect))
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
            raw_value = max(0, _effect_value(effect))
            damage_type = _effect_damage_type(effect)
            multiplier = _calculate_damage_multiplier(
                damage_type,
                actor.merged_immunities,
                actor.merged_resistances,
                actor.merged_vulnerabilities,
            )
            value = max(0, math.floor(raw_value * multiplier))
            actor.hp = max(0, actor.hp - value)
            events.append(
                create_event(
                    EventType.DAMAGE_APPLIED,
                    "damage_applied",
                    {
                        "target_instance_id": actor_instance_id,
                        "amount": value,
                        "damage_type": damage_type.value,
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
            events.append(remove_status_effect_from_actor(actor, actor_instance_id, effect))
            continue
        remaining.append(effect)
    actor.active_status_effects = remaining
    return events

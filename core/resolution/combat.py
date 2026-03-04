from __future__ import annotations

import math
from typing import List

from core.actions import Action
from core.dice import roll_d20, roll_dice
from core.enums import AttackType, DamageType, EventType, SpellType
from core.events import Event, create_event
from core.models.status_effect import StatusEffectInstance
from core.rules import normalize_target_ids, resolve_actor
from core.resolution.status_effects import (
    is_entity_asleep,
    is_entity_restrained,
    is_entity_silenced,
    is_entity_stunned,
    remove_negative_status_effects_from_actor,
)
from core.states.session import (
    GameSessionState,
    find_enemy_by_instance_id,
    find_player_by_instance_id,
)


def calculate_damage_multiplier(
    attack_damage_type: DamageType,
    target_immunities: List[DamageType],
    target_resistances: List[DamageType],
    target_vulnerabilities: List[DamageType],
) -> float:
    if attack_damage_type in target_immunities:
        return 0.0

    has_resistance = attack_damage_type in target_resistances
    has_vulnerability = attack_damage_type in target_vulnerabilities

    if has_resistance and has_vulnerability:
        return 1.0
    if has_resistance:
        return 0.5
    if has_vulnerability:
        return 2.0
    return 1.0


def _apply_status_effects_on_hit(target, status_effects: List[StatusEffectInstance], events: List[Event], target_id: str) -> None:
    for effect in status_effects:
        target.active_status_effects.append(
            StatusEffectInstance(status_effect=effect.status_effect, duration=effect.duration)
        )
        events.append(
            create_event(
                EventType.STATUS_EFFECT_APPLIED,
                "status_effect_applied",
                {
                    "target_instance_id": target_id,
                    "status_effect_id": effect.id,
                    "duration": effect.duration,
                },
            )
        )


def _resolve_attack_targets_for_type(attack_type: AttackType, target_ids: List[str]) -> tuple[List[str], List[str]]:
    single_target_types = {
        AttackType.MELEE,
        AttackType.RANGED,
        AttackType.UNARMED,
    }
    aoe_types = {
        AttackType.AOE_MELEE,
        AttackType.AOE_RANGED,
        AttackType.AOE_UNARMED,
    }

    if attack_type in aoe_types:
        return target_ids, []

    if attack_type in single_target_types and len(target_ids) != 1:
        return [], ["Single-target attacks require exactly one target"]

    return target_ids[:1], []


def _damage_amount_for_attack(attack, target) -> int:
    raw_damage = roll_dice(attack.magnitude).total
    base_damage = max(0, raw_damage)
    damage_types = attack.damage_types or [DamageType.FORCE]
    primary_damage_type = damage_types[0]
    multiplier = calculate_damage_multiplier(
        primary_damage_type,
        target.merged_immunities,
        target.merged_resistances,
        target.merged_vulnerabilities,
    )
    return max(0, math.floor(base_damage * multiplier))


def _damage_amount_for_spell(spell, target) -> int:
    raw_damage = roll_dice(spell.magnitude).total
    base_damage = max(0, raw_damage)
    damage_types = spell.damage_types or [DamageType.FORCE]
    primary_damage_type = damage_types[0]
    multiplier = calculate_damage_multiplier(
        primary_damage_type,
        target.merged_immunities,
        target.merged_resistances,
        target.merged_vulnerabilities,
    )
    return max(0, math.floor(base_damage * multiplier))


def _is_aoe_spell(spell_type: SpellType) -> bool:
    return spell_type in {
        SpellType.AOE_ATTACK,
        SpellType.AOE_HEAL,
        SpellType.AOE_BUFF,
        SpellType.AOE_DEBUFF,
        SpellType.AOE_CONTROL,
        SpellType.AOE_CLEANSE,
    }


def _resolve_spell_targets_for_type(spell_type: SpellType, target_ids: List[str]) -> tuple[List[str], List[str]]:
    if _is_aoe_spell(spell_type):
        return target_ids, []

    if len(target_ids) != 1:
        return [], ["Single-target spells require exactly one target"]

    return target_ids[:1], []


def _is_heal_spell(spell_type: SpellType) -> bool:
    return spell_type in {SpellType.HEAL, SpellType.AOE_HEAL}


def _is_cleanse_spell(spell_type: SpellType) -> bool:
    return spell_type in {SpellType.CLEANSE, SpellType.AOE_CLEANSE}


def _is_status_only_spell(spell_type: SpellType) -> bool:
    return spell_type in {
        SpellType.BUFF,
        SpellType.DEBUFF,
        SpellType.CONTROL,
        SpellType.AOE_BUFF,
        SpellType.AOE_DEBUFF,
        SpellType.AOE_CONTROL,
    }


def _remove_status_effects_from_target(target, effect_ids: set[str], events: List[Event], target_id: str) -> None:
    remaining_effects = []
    for effect in target.active_status_effects:
        if effect_ids and effect.id not in effect_ids:
            remaining_effects.append(effect)
            continue
        events.append(
            create_event(
                EventType.STATUS_EFFECT_REMOVED,
                "status_effect_removed",
                {
                    "actor_instance_id": target_id,
                    "status_effect_id": effect.id,
                },
            )
        )
    target.active_status_effects = remaining_effects


def _spell_effect_succeeds(spell, caster, target, target_id: str, events: List[Event]) -> bool:
    if spell.DC > 0:
        save_roll = roll_d20()
        events.append(
            create_event(
                EventType.DICE_ROLLED,
                "dice_rolled",
                {
                    "actor_instance_id": target_id,
                    "roll_type": "saving_throw",
                    "roll": save_roll,
                    "dc": spell.DC,
                },
            )
        )
        return save_roll < spell.DC

    return True


def _attack_control_lock_errors(actor) -> List[str]:
    errors: List[str] = []
    if is_entity_stunned(actor):
        errors.append("Actor is stunned")
    if is_entity_asleep(actor):
        errors.append("Actor is asleep")
    if is_entity_restrained(actor):
        errors.append("Actor is restrained")
    return errors


def _spell_control_lock_errors(actor) -> List[str]:
    errors: List[str] = []
    if is_entity_stunned(actor):
        errors.append("Actor is stunned")
    if is_entity_asleep(actor):
        errors.append("Actor is asleep")
    if is_entity_silenced(actor):
        errors.append("Actor is silenced")
    return errors


def resolve_attack_action(session: GameSessionState, encounter, action: Action) -> List[Event]:
    target_ids = normalize_target_ids(action.parameters.get("target_instance_ids", []))
    if not isinstance(action.parameters.get("target_instance_ids", []), (str, list)):
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Invalid target_instance_ids"]})]
    if not target_ids:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Missing targets"]})]

    actor = resolve_actor(session, action.actor_instance_id)
    if actor is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Actor not found"]})]

    lock_errors = _attack_control_lock_errors(actor)
    if lock_errors:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": lock_errors})]

    attack_id = str(action.parameters.get("attack_id", "")).strip()
    attack = next((item for item in actor.merged_attacks if item.id == attack_id), None)
    if attack is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": [f"Unknown attack '{attack_id}'"]})]

    resolved_targets, target_errors = _resolve_attack_targets_for_type(attack.type, target_ids)
    if target_errors:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": target_errors})]

    events: List[Event] = [
        create_event(
            EventType.ATTACK_DECLARED,
            "attack_declared",
            {"actor_instance_id": action.actor_instance_id, "attack_id": attack_id},
        )
    ]

    for target_id in resolved_targets:
        target_player = find_player_by_instance_id(session, target_id)
        target_enemy = find_enemy_by_instance_id(encounter, target_id)
        target = target_player or target_enemy
        if target is None:
            events.append(
                create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": [f"Unknown target '{target_id}'"]})
            )
            continue

        if attack.DC > 0:
            save_roll = roll_d20()
            events.append(
                create_event(
                    EventType.DICE_ROLLED,
                    "dice_rolled",
                    {
                        "actor_instance_id": target_id,
                        "roll_type": "saving_throw",
                        "roll": save_roll,
                        "dc": attack.DC,
                    },
                )
            )
            is_hit = save_roll < attack.DC
        else:
            attack_roll = roll_d20() + attack.hit_modifiers
            events.append(
                create_event(
                    EventType.DICE_ROLLED,
                    "dice_rolled",
                    {
                        "actor_instance_id": action.actor_instance_id,
                        "target_instance_id": target_id,
                        "roll_type": "attack_roll",
                        "roll": attack_roll,
                        "target_ac": target.AC,
                        "hit_modifiers": attack.hit_modifiers,
                    },
                )
            )
            is_hit = attack_roll >= target.AC

        if not is_hit:
            events.append(
                create_event(
                    EventType.ATTACK_MISSED,
                    "attack_missed",
                    {
                        "target_instance_id": target_id,
                        "attack_id": attack_id,
                    },
                )
            )
            continue

        damage = _damage_amount_for_attack(attack, target)
        target.hp = max(0, target.hp - damage)
        events.append(
            create_event(
                EventType.ATTACK_HIT,
                "attack_hit",
                {
                    "target_instance_id": target_id,
                    "attack_id": attack_id,
                },
            )
        )
        events.append(create_event(EventType.DAMAGE_APPLIED, "damage_applied", {"target_instance_id": target_id, "amount": damage}))
        events.append(create_event(EventType.HP_UPDATED, "hp_updated", {"target_instance_id": target_id, "hp": target.hp}))
        _apply_status_effects_on_hit(target, attack.applied_status_effects, events, target_id)
        if target.hp == 0:
            events.append(create_event(EventType.DEATH, "death", {"target_instance_id": target_id}))

    return events


def resolve_cast_spell_action(session: GameSessionState, encounter, action: Action) -> List[Event]:
    target_ids = normalize_target_ids(action.parameters.get("target_instance_ids", []))
    if not isinstance(action.parameters.get("target_instance_ids", []), (str, list)):
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Invalid target_instance_ids"]})]
    if not target_ids:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Missing targets"]})]

    caster = resolve_actor(session, action.actor_instance_id)
    if caster is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Actor not found"]})]

    lock_errors = _spell_control_lock_errors(caster)
    if lock_errors:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": lock_errors})]

    spell_id = str(action.parameters.get("spell_id", "")).strip()
    spell = next((item for item in caster.merged_spells if item.id == spell_id), None)
    if spell is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": [f"Unknown spell '{spell_id}'"]})]

    resolved_targets, target_errors = _resolve_spell_targets_for_type(spell.type, target_ids)
    if target_errors:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": target_errors})]

    caster.spell_slots = max(0, caster.spell_slots - spell.spell_cost)
    events: List[Event] = [
        create_event(EventType.SPELL_CAST, "spell_cast", {"spell_id": spell_id, "actor_instance_id": action.actor_instance_id})
    ]
    events.append(
        create_event(
            EventType.MANA_UPDATED,
            "mana_updated",
            {
                "actor_instance_id": action.actor_instance_id,
                "spell_slots": caster.spell_slots,
            },
        )
    )

    for target_id in resolved_targets:
        target_player = find_player_by_instance_id(session, target_id)
        target_enemy = find_enemy_by_instance_id(encounter, target_id)
        target = target_player or target_enemy
        if target is None:
            events.append(
                create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": [f"Unknown target '{target_id}'"]})
            )
            continue

        if _is_heal_spell(spell.type):
            amount = max(0, roll_dice(spell.magnitude).total)
            target.hp = min(target.max_hp, target.hp + amount)
            events.append(create_event(EventType.HEALING_APPLIED, "healing_applied", {"target_instance_id": target_id, "amount": amount}))
            events.append(create_event(EventType.HP_UPDATED, "hp_updated", {"target_instance_id": target_id, "hp": target.hp}))
            _apply_status_effects_on_hit(target, spell.applied_status_effects, events, target_id)
            continue

        if _is_cleanse_spell(spell.type):
            events.extend(remove_negative_status_effects_from_actor(target, target_id))
            continue

        did_affect_target = _spell_effect_succeeds(spell, caster, target, target_id, events)
        if not did_affect_target:
            events.append(
                create_event(
                    EventType.ATTACK_MISSED,
                    "attack_missed",
                    {
                        "target_instance_id": target_id,
                        "spell_id": spell_id,
                    },
                )
            )
            continue

        if _is_status_only_spell(spell.type):
            _apply_status_effects_on_hit(target, spell.applied_status_effects, events, target_id)
            continue

        amount = _damage_amount_for_spell(spell, target)
        events.append(
            create_event(
                EventType.ATTACK_HIT,
                "attack_hit",
                {
                    "target_instance_id": target_id,
                    "spell_id": spell_id,
                },
            )
        )
        target.hp = max(0, target.hp - amount)
        events.append(create_event(EventType.DAMAGE_APPLIED, "damage_applied", {"target_instance_id": target_id, "amount": amount}))
        events.append(create_event(EventType.HP_UPDATED, "hp_updated", {"target_instance_id": target_id, "hp": target.hp}))
        _apply_status_effects_on_hit(target, spell.applied_status_effects, events, target_id)
        if target.hp == 0:
            events.append(create_event(EventType.DEATH, "death", {"target_instance_id": target_id}))

    return events

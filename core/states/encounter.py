from __future__ import annotations

from typing import List, Optional

from core.actions import Action
from core.enums import EventType, GameState
from core.events import Event, create_event
from core.states.session import (
    EncounterStateData,
    GameSessionState,
    alive_enemies,
    alive_players,
    find_enemy_by_instance_id,
    find_player_by_instance_id,
    get_active_encounter,
)


def start_encounter(session: GameSessionState, encounter) -> List[Event]:
    player_ids = [player.player_instance_id for player in alive_players(session.party)]
    enemy_ids = [enemy.enemy_instance_id for enemy in alive_enemies(encounter)]
    session.encounter.turn_order = player_ids + enemy_ids
    session.encounter.current_turn_index = 0
    session.encounter.round_number = 1

    events: List[Event] = []
    for actor_id in session.encounter.turn_order:
        events.append(
            create_event(
                EventType.INITIATIVE_ROLLED,
                "initiative_rolled",
                {"actor_instance_id": actor_id},
            )
        )
    return events


def handle_attack(session: GameSessionState, action: Action) -> List[Event]:
    encounter = get_active_encounter(session)
    if encounter is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["No active encounter"]})]

    target_ids_raw = action.parameters.get("target_instance_ids", [])
    target_ids: List[str]
    if isinstance(target_ids_raw, str):
        target_ids = [target_ids_raw]
    elif isinstance(target_ids_raw, list):
        target_ids = [str(value) for value in target_ids_raw]
    else:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Invalid target_instance_ids"]})]

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

    events.extend(check_encounter_end(session, encounter))
    return events


def handle_cast_spell(session: GameSessionState, action: Action) -> List[Event]:
    encounter = get_active_encounter(session)
    if encounter is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["No active encounter"]})]

    target_ids_raw = action.parameters.get("target_instance_ids", [])
    target_ids: List[str]
    if isinstance(target_ids_raw, str):
        target_ids = [target_ids_raw]
    elif isinstance(target_ids_raw, list):
        target_ids = [str(value) for value in target_ids_raw]
    else:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Invalid target_instance_ids"]})]

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

    events.extend(check_encounter_end(session, encounter))
    return events


def tick_status_effects(session: GameSessionState, actor_instance_id: str) -> List[Event]:
    target_player = find_player_by_instance_id(session, actor_instance_id)
    encounter = get_active_encounter(session)
    target_enemy = find_enemy_by_instance_id(encounter, actor_instance_id) if encounter is not None else None
    actor = target_player or target_enemy
    if actor is None:
        return []

    events: List[Event] = []
    remaining = []
    for effect in actor.active_status_effects:
        effect.duration -= 1
        events.append(create_event(EventType.STATUS_EFFECT_TICKED, "status_effect_ticked", {"actor_instance_id": actor_instance_id, "status_effect_id": effect.id, "duration": effect.duration}))
        if effect.duration <= 0:
            events.append(create_event(EventType.STATUS_EFFECT_REMOVED, "status_effect_removed", {"actor_instance_id": actor_instance_id, "status_effect_id": effect.id}))
            continue
        remaining.append(effect)
    actor.active_status_effects = remaining
    return events


def advance_turn(session: GameSessionState) -> List[Event]:
    if not session.encounter.turn_order:
        return []

    session.encounter.current_turn_index += 1
    if session.encounter.current_turn_index >= len(session.encounter.turn_order):
        session.encounter.current_turn_index = 0
        session.encounter.round_number += 1
        return [create_event(EventType.ROUND_STARTED, "round_started", {"round": session.encounter.round_number})]

    actor_id = session.encounter.turn_order[session.encounter.current_turn_index]
    return [create_event(EventType.TURN_STARTED, "turn_started", {"actor_instance_id": actor_id})]


def handle_end_turn(session: GameSessionState) -> List[Event]:
    if not session.encounter.turn_order:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["No active turn order"]})]

    actor_id = session.encounter.turn_order[session.encounter.current_turn_index]
    events = [create_event(EventType.TURN_ENDED, "turn_ended", {"actor_instance_id": actor_id})]
    events.extend(tick_status_effects(session, actor_id))
    events.extend(advance_turn(session))
    return events


def check_encounter_end(session: GameSessionState, encounter) -> List[Event]:
    from core.states.exploration import check_transition_to_postgame
    from core.states.postgame import build_postgame_summary

    alive_party = alive_players(session.party)
    alive_hostiles = alive_enemies(encounter)

    if alive_hostiles and alive_party:
        return []

    events: List[Event] = [create_event(EventType.ENCOUNTER_ENDED, "encounter_ended", {"encounter_id": encounter.id})]

    if not alive_hostiles:
        encounter.cleared = True
        if session.dungeon is not None:
            from core.states.session import find_room

            room = find_room(session.dungeon, session.exploration.current_room_id)
            if room is not None:
                room.is_cleared = all(item.cleared for item in room.encounters)

        session.state = GameState.EXPLORATION
        session.encounter = EncounterStateData()
        events.append(create_event(EventType.GAME_STATE_CHANGED, "state_changed", {"state": session.state.value}))
        events.extend(check_transition_to_postgame(session))
        return events

    session.state = GameState.POSTGAME
    session.postgame.outcome = "defeat"
    session.postgame.summary = build_postgame_summary(session)
    events.append(create_event(EventType.GAME_STATE_CHANGED, "state_changed", {"state": session.state.value}))
    events.append(create_event(EventType.GAME_FINISHED, "game_finished", {"outcome": "defeat"}))
    return events

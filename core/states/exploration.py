from __future__ import annotations

from typing import List

from core.actions import Action
from core.enums import EventType, GameState, RestType
from core.events import Event, create_event
from core.states.session import (
    GameSessionState,
    ensure_enemy_instance_ids,
    find_room,
    first_uncleared_encounter,
)


def handle_move(session: GameSessionState, action: Action) -> List[Event]:
    if session.dungeon is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Dungeon not selected"]})]

    destination_room_id = str(action.parameters.get("destination_room_id", ""))
    current_room = find_room(session.dungeon, session.exploration.current_room_id)
    destination = find_room(session.dungeon, destination_room_id)

    if current_room is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Current room not found"]})]
    if destination is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Destination room not found"]})]
    if destination_room_id not in current_room.connections:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Destination room is not connected"]})]

    session.exploration.current_room_id = destination_room_id
    destination.is_visited = True

    events = [
        create_event(EventType.MOVEMENT_RESOLVED, "movement_resolved", {"destination_room_id": destination_room_id}),
        create_event(EventType.ROOM_ENTERED, "room_entered", {"room_id": destination_room_id}),
    ]
    events.extend(check_transition_to_encounter(session))
    events.extend(check_transition_to_postgame(session))
    return events


def handle_explore(session: GameSessionState) -> List[Event]:
    if session.dungeon is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Dungeon not selected"]})]

    current_room = find_room(session.dungeon, session.exploration.current_room_id)
    if current_room is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Current room not found"]})]

    return [
        create_event(
            EventType.ROOM_EXPLORED,
            "room_explored",
            {"room_id": current_room.id, "description": current_room.description},
        )
    ]


def handle_rest(session: GameSessionState, action: Action) -> List[Event]:
    if session.dungeon is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Dungeon not selected"]})]

    current_room = find_room(session.dungeon, session.exploration.current_room_id)
    if current_room is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Current room not found"]})]
    if current_room.is_rested:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Room already rested"]})]

    rest_type_raw = str(action.parameters.get("rest_type", ""))
    try:
        rest_type = RestType(rest_type_raw)
    except ValueError:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Invalid rest_type"]})]

    if rest_type not in current_room.allowed_rests:
        return [
            create_event(
                EventType.ACTION_REJECTED,
                "action_rejected",
                {"errors": ["Rest type not allowed in this room"]},
            )
        ]

    for player in session.party:
        if rest_type == RestType.LONG:
            player.hp = player.max_hp
            player.spell_slots = player.max_spell_slots
        else:
            player.hp = min(player.max_hp, player.hp + max(1, player.max_hp // 2))

    current_room.is_rested = True
    return [
        create_event(EventType.REST_STARTED, "rest_started", {"rest_type": rest_type.value}),
        create_event(EventType.REST_COMPLETED, "rest_completed", {"rest_type": rest_type.value}),
    ]


def check_transition_to_encounter(session: GameSessionState) -> List[Event]:
    from core.states.encounter import start_encounter

    if session.dungeon is None:
        return []

    current_room = find_room(session.dungeon, session.exploration.current_room_id)
    if current_room is None:
        return []

    encounter = first_uncleared_encounter(current_room)
    if encounter is None:
        return []

    session.state = GameState.ENCOUNTER
    session.encounter.active_encounter_id = encounter.id
    ensure_enemy_instance_ids(encounter)
    return [
        create_event(EventType.GAME_STATE_CHANGED, "state_changed", {"state": session.state.value}),
        create_event(EventType.ENCOUNTER_STARTED, "encounter_started", {"encounter_id": encounter.id}),
        *start_encounter(session, encounter),
    ]


def check_transition_to_postgame(session: GameSessionState) -> List[Event]:
    from core.states.postgame import build_postgame_summary

    if session.dungeon is None:
        return []
    if session.exploration.current_room_id != session.dungeon.end_room:
        return []

    room = find_room(session.dungeon, session.dungeon.end_room)
    if room is None or not room.is_cleared:
        return []

    session.state = GameState.POSTGAME
    session.postgame.outcome = "victory"
    session.postgame.summary = build_postgame_summary(session)
    return [
        create_event(EventType.GAME_STATE_CHANGED, "state_changed", {"state": session.state.value}),
        create_event(EventType.GAME_FINISHED, "game_finished", {"outcome": "victory"}),
    ]

from __future__ import annotations

from typing import List

from core.enums import EventType, GameState
from core.events import Event, create_event
from core.states.session import (
    EncounterStateData,
    GameSessionState,
    alive_enemies,
    alive_players,
)


def resolve_advance_turn(session: GameSessionState) -> List[Event]:
    if not session.encounter.turn_order:
        return []

    session.encounter.current_turn_index += 1
    if session.encounter.current_turn_index >= len(session.encounter.turn_order):
        session.encounter.current_turn_index = 0
        session.encounter.round_number += 1
        return [create_event(EventType.ROUND_STARTED, "round_started", {"round": session.encounter.round_number})]

    actor_id = session.encounter.turn_order[session.encounter.current_turn_index]
    return [create_event(EventType.TURN_STARTED, "turn_started", {"actor_instance_id": actor_id})]


def resolve_encounter_end(session: GameSessionState, encounter) -> List[Event]:
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

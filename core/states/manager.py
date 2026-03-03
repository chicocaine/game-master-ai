from __future__ import annotations

from typing import Dict, List

from core.actions import Action
from core.validation import validate_action_with_details
from core.enums import ActionType, EventType, GameState
from core.events import Event, create_event
from core.states.encounter import handle_attack, handle_cast_spell, handle_end_turn
from core.states.exploration import handle_explore, handle_move, handle_rest
from core.states.postgame import build_postgame_summary, handle_finish
from core.states.pregame import (
    handle_choose_dungeon,
    handle_create_player,
    handle_remove_player,
    handle_start,
)
from core.states.session import GameSessionState


GLOBAL_ACTIONS = {
    ActionType.ABANDON,
    ActionType.QUERY,
    ActionType.CONVERSE,
}


STATE_ACTIONS: Dict[GameState, set[ActionType]] = {
    GameState.PREGAME: {
        ActionType.CREATE_PLAYER,
        ActionType.REMOVE_PLAYER,
        ActionType.CHOOSE_DUNGEON,
        ActionType.START,
    },
    GameState.EXPLORATION: {
        ActionType.MOVE,
        ActionType.EXPLORE,
        ActionType.REST,
    },
    GameState.ENCOUNTER: {
        ActionType.ATTACK,
        ActionType.CAST_SPELL,
        ActionType.END_TURN,
    },
    GameState.POSTGAME: {
        ActionType.FINISH,
    },
}


def validate_action_for_state(session: GameSessionState, action: Action) -> List[str]:
    return validate_action_with_details(session, action).errors


def apply_action(session: GameSessionState, action: Action) -> List[Event]:
    errors = validate_action_for_state(session, action)
    if errors:
        return [
            create_event(
                EventType.ACTION_REJECTED,
                "action_rejected",
                {"errors": errors, "action_type": action.type.value},
            )
        ]

    session.turn += 1
    events: List[Event] = [
        create_event(
            EventType.ACTION_SUBMITTED,
            "action_submitted",
            {"action_type": action.type.value, "actor_instance_id": action.actor_instance_id},
        )
    ]

    if action.type == ActionType.ABANDON:
        return events + _handle_abandon(session)
    if action.type in {ActionType.QUERY, ActionType.CONVERSE}:
        return events + [create_event(EventType.ACTION_RESOLVED, "action_resolved", {"action_type": action.type.value})]

    if session.state == GameState.PREGAME:
        events.extend(_handle_pregame_action(session, action))
    elif session.state == GameState.EXPLORATION:
        events.extend(_handle_exploration_action(session, action))
    elif session.state == GameState.ENCOUNTER:
        events.extend(_handle_encounter_action(session, action))
    elif session.state == GameState.POSTGAME:
        events.extend(_handle_postgame_action(session, action))

    return events


def _handle_abandon(session: GameSessionState) -> List[Event]:
    session.state = GameState.POSTGAME
    session.postgame.outcome = "abandoned"
    session.postgame.summary = build_postgame_summary(session)
    return [
        create_event(EventType.GAME_STATE_CHANGED, "state_changed", {"state": session.state.value}),
        create_event(EventType.GAME_FINISHED, "game_finished", {"outcome": "abandoned"}),
    ]


def _handle_pregame_action(session: GameSessionState, action: Action) -> List[Event]:
    if action.type == ActionType.CREATE_PLAYER:
        return handle_create_player(session, action)
    if action.type == ActionType.REMOVE_PLAYER:
        return handle_remove_player(session, action)
    if action.type == ActionType.CHOOSE_DUNGEON:
        return handle_choose_dungeon(session, action)
    if action.type == ActionType.START:
        return handle_start(session)
    return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Unsupported pregame action"]})]


def _handle_exploration_action(session: GameSessionState, action: Action) -> List[Event]:
    if action.type == ActionType.MOVE:
        return handle_move(session, action)
    if action.type == ActionType.EXPLORE:
        return handle_explore(session)
    if action.type == ActionType.REST:
        return handle_rest(session, action)
    return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Unsupported exploration action"]})]


def _handle_encounter_action(session: GameSessionState, action: Action) -> List[Event]:
    if action.type == ActionType.ATTACK:
        return handle_attack(session, action)
    if action.type == ActionType.CAST_SPELL:
        return handle_cast_spell(session, action)
    if action.type == ActionType.END_TURN:
        return handle_end_turn(session)
    return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Unsupported encounter action"]})]


def _handle_postgame_action(session: GameSessionState, action: Action) -> List[Event]:
    if action.type == ActionType.FINISH:
        return handle_finish(session)
    return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Unsupported postgame action"]})]

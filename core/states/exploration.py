from __future__ import annotations

from typing import List

from core.actions import Action
from core.events import Event
from core.resolution import (
    resolve_explore_action,
    resolve_move_action,
    resolve_rest_action,
    resolve_transition_to_encounter,
    resolve_transition_to_postgame,
)
from core.states.session import GameSessionState


def handle_move(session: GameSessionState, action: Action) -> List[Event]:
    return resolve_move_action(session, action)


def handle_explore(session: GameSessionState) -> List[Event]:
    return resolve_explore_action(session)


def handle_rest(session: GameSessionState, action: Action) -> List[Event]:
    return resolve_rest_action(session, action)


def check_transition_to_encounter(session: GameSessionState) -> List[Event]:
    return resolve_transition_to_encounter(session)


def check_transition_to_postgame(session: GameSessionState) -> List[Event]:
    return resolve_transition_to_postgame(session)

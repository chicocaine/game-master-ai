from __future__ import annotations

from typing import List

from core.actions import Action
from core.events import Event
from core.resolution import (
    resolve_choose_dungeon_action,
    resolve_create_player_action,
    resolve_remove_player_action,
    resolve_start_action,
)
from core.states.session import GameSessionState


def handle_create_player(session: GameSessionState, action: Action) -> List[Event]:
    return resolve_create_player_action(session, action)


def handle_remove_player(session: GameSessionState, action: Action) -> List[Event]:
    return resolve_remove_player_action(session, action)


def handle_choose_dungeon(session: GameSessionState, action: Action) -> List[Event]:
    return resolve_choose_dungeon_action(session, action)


def handle_start(session: GameSessionState) -> List[Event]:
    return resolve_start_action(session)

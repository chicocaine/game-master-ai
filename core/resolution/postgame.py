from __future__ import annotations

from typing import Any, Dict, List

from core.enums import ActionType, EventType, GameState
from core.events import Event, create_event
from core.states.session import (
    EncounterStateData,
    ExplorationStateData,
    GameSessionState,
    PostGameStateData,
    PreGameStateData,
    alive_players,
)


def resolve_build_postgame_summary(session: GameSessionState) -> Dict[str, Any]:
    if session.dungeon is None:
        return {
            "rooms_cleared": 0,
            "encounters_cleared": 0,
            "players_alive": len(alive_players(session.party)),
        }

    rooms_cleared = sum(1 for room in session.dungeon.rooms if room.is_cleared)
    encounters_cleared = sum(1 for room in session.dungeon.rooms for encounter in room.encounters if encounter.cleared)
    return {
        "rooms_cleared": rooms_cleared,
        "encounters_cleared": encounters_cleared,
        "players_alive": len(alive_players(session.party)),
    }


def resolve_finish_action(session: GameSessionState) -> List[Event]:
    session.state = GameState.PREGAME
    session.party = []
    session.dungeon_id = ""
    session.dungeon = None
    session.pregame = PreGameStateData(started=False)
    session.exploration = ExplorationStateData()
    session.encounter = EncounterStateData()
    session.postgame = PostGameStateData()
    return [
        create_event(EventType.GAME_STATE_CHANGED, "state_changed", {"state": session.state.value}),
        create_event(EventType.ACTION_RESOLVED, "action_resolved", {"action_type": ActionType.FINISH.value}),
    ]

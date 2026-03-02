from __future__ import annotations

from typing import List

from core.actions import Action
from core.enums import EventType, GameState
from core.events import Event, create_event
from core.states.session import (
    GameSessionState,
    clone_dungeon,
    clone_player_from_template,
    find_room,
)


def handle_create_player(session: GameSessionState, action: Action) -> List[Event]:
    entity_id = str(action.parameters.get("entity_id", ""))
    if not entity_id:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Missing entity_id"]})]

    template = session.player_templates.get(entity_id)
    if template is None:
        return [
            create_event(
                EventType.ACTION_REJECTED,
                "action_rejected",
                {"errors": [f"Unknown player template '{entity_id}'"]},
            )
        ]

    explicit_id = str(action.parameters.get("player_instance_id", "")).strip()
    player_instance_id = explicit_id or f"plr_inst_{len(session.party) + 1}"
    player = clone_player_from_template(template, player_instance_id)
    session.party.append(player)

    return [
        create_event(
            EventType.PLAYER_CREATED,
            "player_created",
            {"entity_id": entity_id, "player_instance_id": player.player_instance_id},
        )
    ]


def handle_remove_player(session: GameSessionState, action: Action) -> List[Event]:
    player_instance_id = str(action.parameters.get("player_instance_id", ""))
    if not player_instance_id:
        return [
            create_event(
                EventType.ACTION_REJECTED,
                "action_rejected",
                {"errors": ["Missing player_instance_id"]},
            )
        ]

    updated_party = [player for player in session.party if player.player_instance_id != player_instance_id]
    if len(updated_party) == len(session.party):
        return [
            create_event(
                EventType.ACTION_REJECTED,
                "action_rejected",
                {"errors": [f"Player '{player_instance_id}' not in party"]},
            )
        ]

    session.party = updated_party
    return [
        create_event(
            EventType.PLAYER_REMOVED,
            "player_removed",
            {"player_instance_id": player_instance_id},
        )
    ]


def handle_choose_dungeon(session: GameSessionState, action: Action) -> List[Event]:
    dungeon_id = str(action.parameters.get("dungeon_id", ""))
    if not dungeon_id:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Missing dungeon_id"]})]

    template = session.dungeon_templates.get(dungeon_id)
    if template is None:
        return [
            create_event(
                EventType.ACTION_REJECTED,
                "action_rejected",
                {"errors": [f"Unknown dungeon template '{dungeon_id}'"]},
            )
        ]

    session.dungeon_id = dungeon_id
    session.dungeon = clone_dungeon(template)
    return [create_event(EventType.DUNGEON_CHOSEN, "dungeon_chosen", {"dungeon_id": dungeon_id})]


def handle_start(session: GameSessionState) -> List[Event]:
    from core.states.exploration import check_transition_to_encounter

    if not session.party:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Cannot start without party"]})]
    if session.dungeon is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["Cannot start without dungeon"]})]

    session.state = GameState.EXPLORATION
    session.pregame.started = True
    session.exploration.current_room_id = session.dungeon.start_room

    events: List[Event] = [
        create_event(EventType.GAME_STARTED, "game_started", {"dungeon_id": session.dungeon_id}),
        create_event(EventType.GAME_STATE_CHANGED, "state_changed", {"state": session.state.value}),
    ]

    current_room = find_room(session.dungeon, session.exploration.current_room_id)
    if current_room is not None:
        current_room.is_visited = True
        events.append(create_event(EventType.ROOM_ENTERED, "room_entered", {"room_id": current_room.id}))
        events.extend(check_transition_to_encounter(session))

    return events

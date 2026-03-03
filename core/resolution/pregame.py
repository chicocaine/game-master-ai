from __future__ import annotations

from typing import List

from core.actions import Action
from core.enums import EventType, GameState
from core.events import Event, create_event
from core.rules import can_start_session, normalize_violations
from core.registry.catalog_registry import load_catalog_registry
from core.resolution.exploration import resolve_transition_to_encounter
from core.states.session import (
    GameSessionState,
    clone_dungeon,
    find_room,
)


def resolve_create_player_action(session: GameSessionState, action: Action) -> List[Event]:
    name = str(action.parameters.get("name", "")).strip()
    description = str(action.parameters.get("description", "")).strip()
    race_id = str(action.parameters.get("race", "")).strip()
    archetype_id = str(action.parameters.get("archetype", "")).strip()
    weapon_ids = [str(item).strip() for item in action.parameters.get("weapons", [])]
    explicit_id = str(action.parameters.get("player_instance_id", "")).strip()
    player_instance_id = explicit_id or f"plr_inst_{len(session.party) + 1}"
    entity_id = str(action.parameters.get("entity_id", "")).strip() or f"player_{player_instance_id}"

    catalog = load_catalog_registry("data")
    if race_id not in catalog.races:
        return [
            create_event(
                EventType.ACTION_REJECTED,
                "action_rejected",
                {"errors": [f"Unknown race '{race_id}'"]},
            )
        ]
    if archetype_id not in catalog.archetypes:
        return [
            create_event(
                EventType.ACTION_REJECTED,
                "action_rejected",
                {"errors": [f"Unknown archetype '{archetype_id}'"]},
            )
        ]

    weapons = []
    for weapon_id in weapon_ids:
        weapon = catalog.weapons.get(weapon_id)
        if weapon is None:
            return [
                create_event(
                    EventType.ACTION_REJECTED,
                    "action_rejected",
                    {"errors": [f"Unknown weapon '{weapon_id}'"]},
                )
            ]
        weapons.append(weapon)

    try:
        from core.models.player import create_player

        player = create_player(
            id=entity_id,
            name=name,
            description=description,
            race=catalog.races[race_id],
            archetype=catalog.archetypes[archetype_id],
            weapons=weapons,
            player_instance_id=player_instance_id,
        )
    except ValueError as exc:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": [str(exc)]})]

    session.party.append(player)

    return [
        create_event(
            EventType.PLAYER_CREATED,
            "player_created",
            {
                "entity_id": entity_id,
                "player_instance_id": player.player_instance_id,
                "race": race_id,
                "archetype": archetype_id,
                "weapons": weapon_ids,
            },
        )
    ]


def resolve_remove_player_action(session: GameSessionState, action: Action) -> List[Event]:
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


def resolve_choose_dungeon_action(session: GameSessionState, action: Action) -> List[Event]:
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


def resolve_start_action(session: GameSessionState) -> List[Event]:
    violations = can_start_session(session)
    if violations:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": normalize_violations(violations)})]

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
        events.extend(resolve_transition_to_encounter(session))

    return events

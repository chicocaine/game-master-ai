from __future__ import annotations

from typing import List

from core.enums import EventType
from core.events import Event, create_event
from core.states.session import GameSessionState, alive_enemies, alive_players


def resolve_start_encounter(session: GameSessionState, encounter) -> List[Event]:
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

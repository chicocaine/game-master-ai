from __future__ import annotations

from typing import List

from core.enums import EventType
from core.events import Event, create_event
from core.states.session import (
    GameSessionState,
    find_enemy_by_instance_id,
    find_player_by_instance_id,
    get_active_encounter,
)


def tick_status_effects_for_actor(session: GameSessionState, actor_instance_id: str) -> List[Event]:
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
        events.append(
            create_event(
                EventType.STATUS_EFFECT_TICKED,
                "status_effect_ticked",
                {
                    "actor_instance_id": actor_instance_id,
                    "status_effect_id": effect.id,
                    "duration": effect.duration,
                },
            )
        )
        if effect.duration <= 0:
            events.append(
                create_event(
                    EventType.STATUS_EFFECT_REMOVED,
                    "status_effect_removed",
                    {
                        "actor_instance_id": actor_instance_id,
                        "status_effect_id": effect.id,
                    },
                )
            )
            continue
        remaining.append(effect)
    actor.active_status_effects = remaining
    return events

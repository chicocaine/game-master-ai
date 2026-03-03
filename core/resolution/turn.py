from __future__ import annotations

from typing import List

from core.enums import EventType
from core.events import Event, create_event
from core.resolution.encounter_flow import resolve_advance_turn
from core.resolution.status_effects import tick_status_effects_for_actor
from core.states.session import GameSessionState


def resolve_end_turn(session: GameSessionState) -> List[Event]:
    if not session.encounter.turn_order:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["No active turn order"]})]

    actor_id = session.encounter.turn_order[session.encounter.current_turn_index]
    events = [create_event(EventType.TURN_ENDED, "turn_ended", {"actor_instance_id": actor_id})]
    events.extend(tick_status_effects_for_actor(session, actor_id))
    events.extend(resolve_advance_turn(session))
    return events

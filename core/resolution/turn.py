from __future__ import annotations

from typing import List

from core.enums import EventType
from core.events import Event, create_event
from core.resolution.status_effects import is_entity_asleep, is_entity_stunned
from core.resolution.encounter_flow import resolve_advance_turn
from core.resolution.status_effects import tick_status_effects_for_actor
from core.rules import resolve_actor
from core.states.session import GameSessionState


def resolve_end_turn(session: GameSessionState) -> List[Event]:
    if not session.encounter.turn_order:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["No active turn order"]})]

    actor_id = session.encounter.turn_order[session.encounter.current_turn_index]
    events = [create_event(EventType.TURN_ENDED, "turn_ended", {"actor_instance_id": actor_id})]
    events.extend(tick_status_effects_for_actor(session, actor_id))
    events.extend(resolve_advance_turn(session, emit_turn_started=False))

    skipped_count = 0
    emitted_turn_started = False
    skipped_turns: List[dict] = []
    while session.encounter.turn_order and skipped_count < len(session.encounter.turn_order):
        if session.encounter.current_turn_index >= len(session.encounter.turn_order):
            break

        next_actor_id = session.encounter.turn_order[session.encounter.current_turn_index]
        next_actor = resolve_actor(session, next_actor_id)
        if next_actor is None:
            break

        skip_reasons = []
        if is_entity_stunned(next_actor):
            skip_reasons.append("stunned")
        if is_entity_asleep(next_actor):
            skip_reasons.append("asleep")

        if not skip_reasons:
            payload = {"actor_instance_id": next_actor_id}
            if skipped_turns:
                payload["preceding_skips"] = list(skipped_turns)
            events.append(create_event(EventType.TURN_STARTED, "turn_started", payload))
            emitted_turn_started = True
            break

        skip_reason_text = ", ".join(skip_reasons)
        skipped_turns.append({"actor_instance_id": next_actor_id, "reasons": list(skip_reasons)})
        events.append(
            create_event(
                EventType.TURN_SKIPPED,
                "turn_skipped",
                {
                    "actor_instance_id": next_actor_id,
                    "reasons": skip_reasons,
                    "turn_skip_reason": skip_reason_text,
                },
            )
        )
        events.extend(tick_status_effects_for_actor(session, next_actor_id))
        events.extend(resolve_advance_turn(session, emit_turn_started=False))
        skipped_count += 1

    if not emitted_turn_started and session.encounter.turn_order and skipped_count < len(session.encounter.turn_order):
        if session.encounter.current_turn_index < len(session.encounter.turn_order):
            next_actor_id = session.encounter.turn_order[session.encounter.current_turn_index]
            payload = {"actor_instance_id": next_actor_id}
            if skipped_turns:
                payload["preceding_skips"] = list(skipped_turns)
            events.append(create_event(EventType.TURN_STARTED, "turn_started", payload))

    return events

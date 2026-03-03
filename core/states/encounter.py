from __future__ import annotations

from typing import List

from core.actions import Action
from core.enums import EventType, GameState
from core.events import Event, create_event
from core.resolution import (
    resolve_advance_turn,
    resolve_attack_action,
    resolve_cast_spell_action,
    resolve_encounter_end,
    resolve_end_turn,
    resolve_start_encounter,
    tick_status_effects_for_actor,
)
from core.states.session import (
    GameSessionState,
    get_active_encounter,
)


def start_encounter(session: GameSessionState, encounter) -> List[Event]:
    return resolve_start_encounter(session, encounter)


def handle_attack(session: GameSessionState, action: Action) -> List[Event]:
    encounter = get_active_encounter(session)
    if encounter is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["No active encounter"]})]
    events = resolve_attack_action(session, encounter, action)

    events.extend(check_encounter_end(session, encounter))
    return events


def handle_cast_spell(session: GameSessionState, action: Action) -> List[Event]:
    encounter = get_active_encounter(session)
    if encounter is None:
        return [create_event(EventType.ACTION_REJECTED, "action_rejected", {"errors": ["No active encounter"]})]
    events = resolve_cast_spell_action(session, encounter, action)

    events.extend(check_encounter_end(session, encounter))
    return events


def tick_status_effects(session: GameSessionState, actor_instance_id: str) -> List[Event]:
    return tick_status_effects_for_actor(session, actor_instance_id)


def advance_turn(session: GameSessionState) -> List[Event]:
    return resolve_advance_turn(session)


def handle_end_turn(session: GameSessionState) -> List[Event]:
    return resolve_end_turn(session)


def check_encounter_end(session: GameSessionState, encounter) -> List[Event]:
    return resolve_encounter_end(session, encounter)

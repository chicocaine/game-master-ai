from __future__ import annotations

import random
from typing import List

from core.dice import roll_d20
from core.enums import EventType
from core.events import Event, create_event
from core.states.session import GameSessionState, alive_enemies, alive_players


def _initiative_modifier(actor: object) -> int:
    value = getattr(actor, "initiative_mod", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def resolve_start_encounter(session: GameSessionState, encounter, rng: random.Random | None = None) -> List[Event]:
    combatants = [
        *alive_players(session.party),
        *alive_enemies(encounter),
    ]

    initiative_rows = []
    for index, actor in enumerate(combatants):
        actor_instance_id = getattr(actor, "player_instance_id", "") or getattr(actor, "enemy_instance_id", "")
        if not actor_instance_id:
            continue

        mod = _initiative_modifier(actor)
        roll = roll_d20(rng=rng)
        total = roll + mod
        initiative_rows.append(
            {
                "actor_instance_id": actor_instance_id,
                "roll": roll,
                "modifier": mod,
                "initiative": total,
                "index": index,
            }
        )

    initiative_rows.sort(key=lambda row: (-row["initiative"], row["index"]))
    session.encounter.turn_order = [row["actor_instance_id"] for row in initiative_rows]
    session.encounter.current_turn_index = 0
    session.encounter.round_number = 1

    events: List[Event] = []
    for row in initiative_rows:
        events.append(
            create_event(
                EventType.INITIATIVE_ROLLED,
                "initiative_rolled",
                {
                    "actor_instance_id": row["actor_instance_id"],
                    "roll": row["roll"],
                    "modifier": row["modifier"],
                    "initiative": row["initiative"],
                },
            )
        )
    return events

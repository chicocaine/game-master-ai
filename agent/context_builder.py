from __future__ import annotations

from typing import Any, Dict, List

from core.states.session import GameSessionState, get_active_encounter


def build_state_context(session: GameSessionState) -> Dict[str, Any]:
    encounter = get_active_encounter(session)
    return {
        "state": session.state.value,
        "turn": session.turn,
        "party": _party_summary(session),
        "encounter": _encounter_summary(encounter),
    }


def _party_summary(session: GameSessionState) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for player in session.party:
        rows.append(
            {
                "player_instance_id": player.player_instance_id,
                "name": player.name,
                "hp": player.hp,
                "max_hp": player.max_hp,
                "spell_slots": player.spell_slots,
                "max_spell_slots": player.max_spell_slots,
            }
        )
    return rows


def _encounter_summary(encounter) -> Dict[str, Any]:
    if encounter is None:
        return {"active": False}

    return {
        "active": True,
        "encounter_id": encounter.id,
        "enemies": [
            {
                "enemy_instance_id": enemy.enemy_instance_id,
                "name": enemy.name,
                "hp": enemy.hp,
                "max_hp": enemy.max_hp,
            }
            for enemy in encounter.enemies
        ],
    }

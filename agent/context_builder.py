from __future__ import annotations

from typing import Any, Dict, List

from core.enums import ActionType, GameState
from core.rules import can_start_session
from core.states.session import GameSessionState, find_room, get_active_encounter


def build_state_context(session: GameSessionState) -> Dict[str, Any]:
    encounter = get_active_encounter(session)
    current_room = _current_room_summary(session)
    return {
        "state": session.state.value,
        "turn": session.turn,
        "legal_actions": _legal_actions_for_state(session.state),
        "pregame": _pregame_summary(session),
        "turn_context": _turn_context(session),
        "dungeon": _dungeon_summary(session, current_room),
        "current_room": current_room,
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
                "status_effects": _status_effects_summary(player.active_status_effects),
                "resistances": [item.value for item in player.merged_resistances],
                "immunities": [item.value for item in player.merged_immunities],
                "vulnerabilities": [item.value for item in player.merged_vulnerabilities],
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
                "status_effects": _status_effects_summary(enemy.active_status_effects),
                "resistances": [item.value for item in enemy.merged_resistances],
                "immunities": [item.value for item in enemy.merged_immunities],
                "vulnerabilities": [item.value for item in enemy.merged_vulnerabilities],
            }
            for enemy in encounter.enemies
        ],
    }


def _status_effects_summary(effects: List[Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for effect in effects:
        status_effect = getattr(effect, "status_effect", None)
        if status_effect is None:
            continue
        rows.append(
            {
                "id": str(getattr(status_effect, "id", "")),
                "name": str(getattr(status_effect, "name", "")),
                "type": str(getattr(getattr(status_effect, "type", ""), "value", getattr(status_effect, "type", ""))),
                "duration": int(getattr(effect, "duration", 0)),
                "parameters": dict(getattr(status_effect, "parameters", {}) or {}),
            }
        )
    return rows


def _legal_actions_for_state(state: GameState) -> List[str]:
    by_state = {
        GameState.PREGAME: [
            ActionType.CREATE_PLAYER,
            ActionType.REMOVE_PLAYER,
            ActionType.CHOOSE_DUNGEON,
            ActionType.START,
            ActionType.ABANDON,
            ActionType.QUERY,
            ActionType.CONVERSE,
        ],
        GameState.EXPLORATION: [
            ActionType.MOVE,
            ActionType.EXPLORE,
            ActionType.REST,
            ActionType.ABANDON,
            ActionType.QUERY,
            ActionType.CONVERSE,
        ],
        GameState.ENCOUNTER: [
            ActionType.ATTACK,
            ActionType.CAST_SPELL,
            ActionType.END_TURN,
            ActionType.ABANDON,
            ActionType.QUERY,
            ActionType.CONVERSE,
        ],
        GameState.POSTGAME: [
            ActionType.FINISH,
            ActionType.ABANDON,
            ActionType.QUERY,
            ActionType.CONVERSE,
        ],
    }
    return [item.value for item in by_state.get(state, [])]


def _current_room_summary(session: GameSessionState) -> Dict[str, Any]:
    if session.dungeon is None or not session.exploration.current_room_id:
        return {"available": False}

    room = find_room(session.dungeon, session.exploration.current_room_id)
    if room is None:
        return {"available": False}

    return {
        "available": True,
        "id": room.id,
        "name": room.name,
        "description": room.description,
        "is_visited": room.is_visited,
        "is_cleared": room.is_cleared,
        "is_rested": room.is_rested,
        "connections": list(room.connections),
        "allowed_rests": [rest.value for rest in room.allowed_rests],
        "encounters": [
            {
                "id": encounter.id,
                "name": encounter.name,
                "cleared": encounter.cleared,
                "enemy_count": len(encounter.enemies),
            }
            for encounter in room.encounters
        ],
    }


def _dungeon_summary(session: GameSessionState, current_room: Dict[str, Any]) -> Dict[str, Any]:
    if session.dungeon is None:
        return {"selected": False}

    total_rooms = len(session.dungeon.rooms)
    cleared_rooms = sum(1 for room in session.dungeon.rooms if room.is_cleared)
    visited_rooms = sum(1 for room in session.dungeon.rooms if room.is_visited)

    return {
        "selected": True,
        "id": session.dungeon.id,
        "name": session.dungeon.name,
        "difficulty": session.dungeon.difficulty.value,
        "start_room": session.dungeon.start_room,
        "end_room": session.dungeon.end_room,
        "total_rooms": total_rooms,
        "visited_rooms": visited_rooms,
        "cleared_rooms": cleared_rooms,
        "progress": {
            "visited_ratio": (visited_rooms / total_rooms) if total_rooms else 0.0,
            "cleared_ratio": (cleared_rooms / total_rooms) if total_rooms else 0.0,
        },
        "current_room_id": str(current_room.get("id", "")),
    }


def _turn_context(session: GameSessionState) -> Dict[str, Any]:
    if session.state != GameState.ENCOUNTER:
        return {"initiative_active": False}

    turn_order = list(session.encounter.turn_order)
    index = session.encounter.current_turn_index
    actor_instance_id = ""
    if turn_order and 0 <= index < len(turn_order):
        actor_instance_id = turn_order[index]

    return {
        "initiative_active": True,
        "round_number": session.encounter.round_number,
        "current_turn_index": index,
        "turn_order": turn_order,
        "active_actor_instance_id": actor_instance_id,
    }


def _pregame_summary(session: GameSessionState) -> Dict[str, Any]:
    race_options: Dict[str, Dict[str, Any]] = {}
    archetype_options: Dict[str, Dict[str, Any]] = {}
    weapon_options: Dict[str, Dict[str, Any]] = {}
    player_template_options: List[Dict[str, Any]] = []

    for template in session.player_templates.values():
        race_options.setdefault(
            template.race.id,
            {
                "id": template.race.id,
                "name": template.race.name,
                "allowed_archetypes": list(template.race.archetype_constraints),
            },
        )
        archetype_options.setdefault(
            template.archetype.id,
            {
                "id": template.archetype.id,
                "name": template.archetype.name,
            },
        )

        for weapon in template.weapons:
            weapon_options.setdefault(
                weapon.id,
                {
                    "id": weapon.id,
                    "name": weapon.name,
                    "proficiency": weapon.proficiency.value,
                    "handling": weapon.handling.value,
                    "weight_class": weapon.weight_class.value,
                    "delivery": weapon.delivery.value,
                    "magic_type": weapon.magic_type.value,
                },
            )

        player_template_options.append(
            {
                "id": template.id,
                "name": template.name,
                "race": template.race.id,
                "archetype": template.archetype.id,
                "weapon_ids": [weapon.id for weapon in template.weapons],
            }
        )

    dungeon_options = [
        {
            "id": dungeon.id,
            "name": dungeon.name,
            "difficulty": dungeon.difficulty.value,
            "room_count": len(dungeon.rooms),
            "start_room": dungeon.start_room,
            "end_room": dungeon.end_room,
        }
        for dungeon in session.dungeon_templates.values()
    ]

    start_violations = can_start_session(session)
    return {
        "active": session.state == GameState.PREGAME,
        "party_size": len(session.party),
        "dungeon_selected": session.dungeon is not None,
        "create_player_required_fields": ["name", "description", "race", "archetype", "weapons"],
        "build_options": {
            "races": sorted(race_options.values(), key=lambda item: item["id"]),
            "archetypes": sorted(archetype_options.values(), key=lambda item: item["id"]),
            "weapons": sorted(weapon_options.values(), key=lambda item: item["id"]),
            "player_templates": sorted(player_template_options, key=lambda item: item["id"]),
            "dungeons": sorted(dungeon_options, key=lambda item: item["id"]),
        },
        "start_readiness": {
            "can_start": not start_violations,
            "missing_requirements": [violation.message for violation in start_violations],
            "missing_codes": [violation.code for violation in start_violations],
        },
    }

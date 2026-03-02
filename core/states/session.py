from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.enums import GameState
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from core.models.player import Player


def _get_str(data: dict, key: str, default: str = "") -> str:
    return str(data.get(key, default))


def _get_int(data: dict, key: str, default: int = 0) -> int:
    return int(data.get(key, default))


def _get_dict(data: dict, key: str) -> Dict[str, Any]:
    value = data.get(key, {})
    if isinstance(value, dict):
        return value
    return {}


def clone_player_from_template(template: Player, player_instance_id: str) -> Player:
    payload = template.to_dict()
    payload["player_instance_id"] = player_instance_id
    return Player.from_dict(payload)


def clone_dungeon(template: Dungeon) -> Dungeon:
    return copy.deepcopy(template)


def serialize_runtime_dungeon(dungeon: Optional[Dungeon]) -> Optional[dict]:
    if dungeon is None:
        return None

    return {
        "id": dungeon.id,
        "name": dungeon.name,
        "description": dungeon.description,
        "difficulty": dungeon.difficulty.value,
        "start_room": dungeon.start_room,
        "end_room": dungeon.end_room,
        "rooms": [serialize_runtime_room(room) for room in dungeon.rooms],
    }


def serialize_runtime_room(room: Room) -> dict:
    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
        "is_visited": room.is_visited,
        "is_cleared": room.is_cleared,
        "is_rested": room.is_rested,
        "connections": list(room.connections),
        "allowed_rests": [rest_type.value for rest_type in room.allowed_rests],
        "encounters": [serialize_runtime_encounter(encounter) for encounter in room.encounters],
    }


def serialize_runtime_encounter(encounter: Encounter) -> dict:
    return {
        "id": encounter.id,
        "name": encounter.name,
        "description": encounter.description,
        "difficulty": encounter.difficulty.value,
        "cleared": encounter.cleared,
        "clear_reward": encounter.clear_reward,
        "enemies": [enemy.to_dict() for enemy in encounter.enemies],
    }


def find_room(dungeon: Dungeon, room_id: str) -> Optional[Room]:
    for room in dungeon.rooms:
        if room.id == room_id:
            return room
    return None


def first_uncleared_encounter(room: Room) -> Optional[Encounter]:
    for encounter in room.encounters:
        if not encounter.cleared:
            return encounter
    return None


def alive_players(players: List[Player]) -> List[Player]:
    return [player for player in players if player.hp > 0]


def alive_enemies(encounter: Encounter) -> List[Enemy]:
    return [enemy for enemy in encounter.enemies if enemy.hp > 0]


def ensure_enemy_instance_ids(encounter: Encounter) -> None:
    for index, enemy in enumerate(encounter.enemies, start=1):
        if not enemy.enemy_instance_id:
            enemy.enemy_instance_id = f"{encounter.id}_enemy_{index}"


def get_active_encounter(session: "GameSessionState") -> Optional[Encounter]:
    if session.dungeon is None:
        return None
    room = find_room(session.dungeon, session.exploration.current_room_id)
    if room is None:
        return None
    for encounter in room.encounters:
        if encounter.id == session.encounter.active_encounter_id:
            return encounter
    return None


def find_enemy_by_instance_id(encounter: Encounter, instance_id: str) -> Optional[Enemy]:
    for enemy in encounter.enemies:
        if enemy.enemy_instance_id == instance_id:
            return enemy
    return None


def find_player_by_instance_id(session: "GameSessionState", instance_id: str) -> Optional[Player]:
    for player in session.party:
        if player.player_instance_id == instance_id:
            return player
    return None


@dataclass
class PreGameStateData:
    started: bool = False

    def to_dict(self) -> dict:
        return {"started": self.started}

    @classmethod
    def from_dict(cls, data: dict) -> "PreGameStateData":
        return cls(started=bool(data.get("started", False)))


@dataclass
class ExplorationStateData:
    current_room_id: str = ""

    def to_dict(self) -> dict:
        return {"current_room_id": self.current_room_id}

    @classmethod
    def from_dict(cls, data: dict) -> "ExplorationStateData":
        return cls(current_room_id=_get_str(data, "current_room_id"))


@dataclass
class EncounterStateData:
    active_encounter_id: str = ""
    turn_order: List[str] = field(default_factory=list)
    current_turn_index: int = 0
    round_number: int = 1

    def to_dict(self) -> dict:
        return {
            "active_encounter_id": self.active_encounter_id,
            "turn_order": list(self.turn_order),
            "current_turn_index": self.current_turn_index,
            "round_number": self.round_number,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EncounterStateData":
        return cls(
            active_encounter_id=_get_str(data, "active_encounter_id"),
            turn_order=[str(item) for item in data.get("turn_order", []) if isinstance(item, str)],
            current_turn_index=_get_int(data, "current_turn_index", 0),
            round_number=_get_int(data, "round_number", 1),
        )


@dataclass
class PostGameStateData:
    outcome: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "summary": dict(self.summary),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PostGameStateData":
        return cls(
            outcome=_get_str(data, "outcome"),
            summary=_get_dict(data, "summary"),
        )


@dataclass
class GameSessionState:
    state: GameState = GameState.PREGAME
    party: List[Player] = field(default_factory=list)
    dungeon_id: str = ""
    dungeon: Optional[Dungeon] = None
    turn: int = 0
    pregame: PreGameStateData = field(default_factory=PreGameStateData)
    exploration: ExplorationStateData = field(default_factory=ExplorationStateData)
    encounter: EncounterStateData = field(default_factory=EncounterStateData)
    postgame: PostGameStateData = field(default_factory=PostGameStateData)
    player_templates: Dict[str, Player] = field(default_factory=dict, repr=False)
    dungeon_templates: Dict[str, Dungeon] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "party": [player.to_dict() for player in self.party],
            "dungeon_id": self.dungeon_id,
            "dungeon": serialize_runtime_dungeon(self.dungeon),
            "turn": self.turn,
            "pregame": self.pregame.to_dict(),
            "exploration": self.exploration.to_dict(),
            "encounter": self.encounter.to_dict(),
            "postgame": self.postgame.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameSessionState":
        dungeon_payload = data.get("dungeon")
        dungeon = Dungeon.from_dict(dungeon_payload) if isinstance(dungeon_payload, dict) else None
        return cls(
            state=GameState(_get_str(data, "state", GameState.PREGAME.value)),
            party=[Player.from_dict(item) for item in data.get("party", []) if isinstance(item, dict)],
            dungeon_id=_get_str(data, "dungeon_id"),
            dungeon=dungeon,
            turn=_get_int(data, "turn", 0),
            pregame=PreGameStateData.from_dict(_get_dict(data, "pregame")),
            exploration=ExplorationStateData.from_dict(_get_dict(data, "exploration")),
            encounter=EncounterStateData.from_dict(_get_dict(data, "encounter")),
            postgame=PostGameStateData.from_dict(_get_dict(data, "postgame")),
        )

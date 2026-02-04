"""Game state models for exploration and encounter modes."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from models.entities import Entity, EntityType


class GameMode(Enum):
    """Enumeration of game modes."""
    EXPLORATION = "exploration"
    ENCOUNTER = "encounter"


class GameResult(Enum):
    """Enumeration of game results."""
    GAME_COMPLETE = "GAME_COMPLETE"
    GAME_OVER = "GAME_OVER"
    ABANDONED = "ABANDONED"
    IN_PROGRESS = "IN_PROGRESS"


@dataclass
class DungeonState:
    """Tracks dungeon exploration metadata."""
    visited_rooms: List[str] = field(default_factory=list)
    rested_rooms: List[str] = field(default_factory=list)

    def mark_visited(self, room_id: str) -> None:
        """Mark a room as visited."""
        if room_id not in self.visited_rooms:
            self.visited_rooms.append(room_id)

    def mark_rested(self, room_id: str) -> None:
        """Mark a room as having been rested in."""
        if room_id not in self.rested_rooms:
            self.rested_rooms.append(room_id)

    def has_rested_in(self, room_id: str) -> bool:
        """Check if party has already rested in a room."""
        return room_id in self.rested_rooms


@dataclass
class Progression:
    """Tracks session rewards and achievements."""
    total_rewards: int = 0
    encounters_cleared: int = 0

    def add_reward(self, amount: int) -> None:
        """Add reward points."""
        self.total_rewards += amount

    def mark_encounter_cleared(self) -> None:
        """Increment cleared encounter counter."""
        self.encounters_cleared += 1


@dataclass
class GlobalGameState:
    """Main game state during exploration mode."""
    game_mode: GameMode = GameMode.EXPLORATION
    current_dungeon_id: str = ""
    current_room_id: str = ""
    players: List[Entity] = field(default_factory=list)
    cleared_encounters: List[str] = field(default_factory=list)
    dungeon_state: DungeonState = field(default_factory=DungeonState)
    progression: Progression = field(default_factory=Progression)

    def get_living_players(self) -> List[Entity]:
        """Get all living players."""
        return [p for p in self.players if p.is_alive()]

    def all_players_dead(self) -> bool:
        """Check if all players are dead."""
        return len(self.get_living_players()) == 0

    def has_cleared_encounter(self, encounter_id: str) -> bool:
        """Check if an encounter has been cleared."""
        return encounter_id in self.cleared_encounters

    def mark_encounter_cleared(self, encounter_id: str, reward: int) -> None:
        """Mark an encounter as cleared and add reward."""
        if encounter_id not in self.cleared_encounters:
            self.cleared_encounters.append(encounter_id)
            self.progression.add_reward(reward)
            self.progression.mark_encounter_cleared()

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "game_mode": self.game_mode.value,
            "current_dungeon_id": self.current_dungeon_id,
            "current_room_id": self.current_room_id,
            "party": {
                "players": [p.to_dict() for p in self.players]
            },
            "cleared_encounters": self.cleared_encounters,
            "dungeon_state": {
                "visited_rooms": self.dungeon_state.visited_rooms,
                "rested_rooms": self.dungeon_state.rested_rooms,
            },
            "progression": {
                "total_rewards": self.progression.total_rewards,
                "encounters_cleared": self.progression.encounters_cleared,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GlobalGameState":
        """Deserialize from dictionary."""
        players = [Entity.from_dict(p) for p in data["party"]["players"]]
        dungeon_state = DungeonState(
            visited_rooms=data["dungeon_state"]["visited_rooms"],
            rested_rooms=data["dungeon_state"]["rested_rooms"],
        )
        progression = Progression(
            total_rewards=data["progression"]["total_rewards"],
            encounters_cleared=data["progression"]["encounters_cleared"],
        )
        return cls(
            game_mode=GameMode(data["game_mode"]),
            current_dungeon_id=data["current_dungeon_id"],
            current_room_id=data["current_room_id"],
            players=players,
            cleared_encounters=data.get("cleared_encounters", []),
            dungeon_state=dungeon_state,
            progression=progression,
        )


@dataclass
class EncounterState:
    """Temporary state during combat."""
    encounter_id: str = ""
    room_id: str = ""
    round: int = 1
    entities: List[Entity] = field(default_factory=list)
    initiative_order: List[str] = field(default_factory=list)
    active_entity_id: str = ""
    combat_log: List[str] = field(default_factory=list)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        for entity in self.entities:
            if entity.entity_id == entity_id:
                return entity
        return None

    def get_living_entities(self) -> List[Entity]:
        """Get all living entities."""
        return [e for e in self.entities if e.is_alive()]

    def get_living_enemies(self) -> List[Entity]:
        """Get all living enemies."""
        return [e for e in self.entities if e.is_alive() and e.entity_type == EntityType.ENEMY]

    def get_living_players(self) -> List[Entity]:
        """Get all living players."""
        return [e for e in self.entities if e.is_alive() and e.entity_type == EntityType.PLAYER]

    def get_active_entity(self) -> Optional[Entity]:
        """Get the currently active entity."""
        return self.get_entity(self.active_entity_id)

    def advance_turn(self) -> None:
        """Advance to next entity in initiative order."""
        try:
            current_index = self.initiative_order.index(self.active_entity_id)
            next_index = (current_index + 1) % len(self.initiative_order)
            self.active_entity_id = self.initiative_order[next_index]
            
            # Increment round if we've cycled back to start
            if next_index == 0:
                self.round += 1
        except ValueError:
            pass  # Active entity not in initiative (shouldn't happen)

    def append_log(self, message: str) -> None:
        """Append message to combat log."""
        self.combat_log.append(message)

    def all_enemies_dead(self) -> bool:
        """Check if all enemies are defeated."""
        return len(self.get_living_enemies()) == 0

    def all_players_dead(self) -> bool:
        """Check if all players are defeated."""
        return len(self.get_living_players()) == 0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "encounter_id": self.encounter_id,
            "room_id": self.room_id,
            "round": self.round,
            "entities": [e.to_dict() for e in self.entities],
            "initiative_order": self.initiative_order,
            "active_entity_id": self.active_entity_id,
            "combat_log": self.combat_log,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EncounterState":
        """Deserialize from dictionary."""
        entities = [Entity.from_dict(e) for e in data["entities"]]
        return cls(
            encounter_id=data["encounter_id"],
            room_id=data["room_id"],
            round=data["round"],
            entities=entities,
            initiative_order=data["initiative_order"],
            active_entity_id=data["active_entity_id"],
            combat_log=data.get("combat_log", []),
        )
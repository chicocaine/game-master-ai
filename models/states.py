from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class GameMode(Enum):
    EXPLORATION = "exploration"
    ENCOUNTER = "encounter"
    GAME_OVER = "game_over"

@dataclass
class GlobalGameState:
    game_mode: GameMode = GameMode.EXPLORATION

    # Dungeon / world state
    dungeon_id: str = ""
    current_node_id: str = ""
    visited_nodes: List[str] = field(default_factory=list)
    cleared_nodes: List[str] = field(default_factory=list)

    # Party state
    players: Dict[str, dict] = field(default_factory=dict)
    party_inventory: Dict[str, int] = field(default_factory=dict)

    # Meta
    turn_counter: int = 0
    narrative_log: List[str] = field(default_factory=list)

    def is_node_cleared(self, node_id: str) -> bool:
        return node_id in self.cleared_nodes

    def mark_node_cleared(self, node_id: str):
        if node_id not in self.cleared_nodes:
            self.cleared_nodes.append(node_id)

@dataclass
class EncounterState:
    encounter_id: str
    node_id: str

    # Combatants
    players: Dict[str, dict]
    enemies: Dict[str, dict]

    # Turn system
    initiative_order: List[str] = field(default_factory=list)
    active_entity_id: Optional[str] = None
    round_number: int = 1

    # Status
    encounter_over: bool = False
    victory: Optional[bool] = None  # True = players win, False = players lose

    # Logs
    combat_log: List[str] = field(default_factory=list)

    def get_entity(self, entity_id: str) -> Optional[dict]:
        if entity_id in self.players:
            return self.players[entity_id]
        if entity_id in self.enemies:
            return self.enemies[entity_id]
        return None

    def all_enemies_defeated(self) -> bool:
        return all(e["hp"] <= 0 for e in self.enemies.values())

    def all_players_defeated(self) -> bool:
        return all(p["hp"] <= 0 for p in self.players.values())

    def advance_turn(self):
        if not self.initiative_order:
            return

        current_index = self.initiative_order.index(self.active_entity_id)
        next_index = (current_index + 1) % len(self.initiative_order)

        self.active_entity_id = self.initiative_order[next_index]

        if next_index == 0:
            self.round_number += 1


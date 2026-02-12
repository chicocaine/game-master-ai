"""Validation engine for actions and state transitions."""

from dataclasses import dataclass, field
from typing import List, Optional

from models.actions import Action, ActionType, RestType
from models.entities import Entity
from models.states import GlobalGameState, EncounterState, GameMode
from models.data_loader import DataLoader


@dataclass
class ValidationResult:
    """Encapsulates validation results."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)

    @classmethod
    def ok(cls) -> "ValidationResult":
        return cls(is_valid=True, errors=[])

    @classmethod
    def fail(cls, *errors: str) -> "ValidationResult":
        return cls(is_valid=False, errors=list(errors))


class ValidationEngine:
    """Validates actions against current game state and data definitions."""

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def validate_action(
        self,
        action: Action,
        global_state: GlobalGameState,
        encounter_state: Optional[EncounterState] = None,
    ) -> ValidationResult:
        """Validate an action based on current game mode and state."""
        if action is None:
            return ValidationResult.fail("Action is missing.")

        if global_state.game_mode == GameMode.EXPLORATION:
            return self._validate_exploration_action(action, global_state)

        if global_state.game_mode == GameMode.ENCOUNTER:
            if encounter_state is None:
                return ValidationResult.fail("Encounter state is required during combat.")
            return self._validate_encounter_action(action, encounter_state)

        return ValidationResult.fail(f"Unsupported game mode: {global_state.game_mode}")

    def _validate_exploration_action(
        self, action: Action, state: GlobalGameState
    ) -> ValidationResult:
        if action.action_type not in {
            ActionType.MOVE,
            ActionType.EXPLORE,
            ActionType.REST,
        }:
            return ValidationResult.fail(
                f"Action '{action.action_type.value}' is invalid in exploration mode."
            )

        if action.action_type == ActionType.MOVE:
            return self._validate_move_action(action, state)

        if action.action_type == ActionType.EXPLORE:
            return ValidationResult.ok()

        if action.action_type == ActionType.REST:
            return self._validate_rest_action(action, state)

        return ValidationResult.fail("Unknown exploration action.")

    def _validate_encounter_action(
        self, action: Action, state: EncounterState
    ) -> ValidationResult:
        if action.action_type not in {
            ActionType.ATTACK,
            ActionType.CAST_SPELL,
            ActionType.END_TURN,
        }:
            return ValidationResult.fail(
                f"Action '{action.action_type.value}' is invalid in encounter mode."
            )

        actor = state.get_entity(action.actor_id)
        if actor is None:
            return ValidationResult.fail("Actor does not exist in this encounter.")

        if not actor.is_alive():
            return ValidationResult.fail("Actor is not alive and cannot act.")

        if state.active_entity_id != action.actor_id:
            return ValidationResult.fail("It is not the actor's turn.")

        if actor.has_status_effect("stunned"):
            return ValidationResult.fail("Actor is stunned and cannot act.")

        if action.action_type == ActionType.ATTACK:
            return self._validate_attack_action(action, state, actor)

        if action.action_type == ActionType.CAST_SPELL:
            return self._validate_cast_spell_action(action, state, actor)

        if action.action_type == ActionType.END_TURN:
            return ValidationResult.ok()

        return ValidationResult.fail("Unknown encounter action.")

    def _validate_move_action(self, action: Action, state: GlobalGameState) -> ValidationResult:
        dungeon = self.data_loader.get_dungeon(state.current_dungeon_id)
        if dungeon is None:
            return ValidationResult.fail("Current dungeon is not loaded.")

        rooms = dungeon.get("rooms", {})
        current_room = rooms.get(state.current_room_id)
        if current_room is None:
            return ValidationResult.fail("Current room does not exist.")

        if not action.target_id:
            return ValidationResult.fail("Move action requires a target room.")

        target_room = rooms.get(action.target_id)
        if target_room is None:
            return ValidationResult.fail("Target room does not exist.")

        connections = current_room.get("connections", [])
        if action.target_id not in connections:
            return ValidationResult.fail("Target room is not connected to current room.")

        return ValidationResult.ok()

    def _validate_rest_action(self, action: Action, state: GlobalGameState) -> ValidationResult:
        rest_type = action.parameters.get("rest_type")
        if rest_type not in {RestType.SHORT.value, RestType.LONG.value}:
            return ValidationResult.fail("Invalid rest type. Use 'short' or 'long'.")

        dungeon = self.data_loader.get_dungeon(state.current_dungeon_id)
        if dungeon is None:
            return ValidationResult.fail("Current dungeon is not loaded.")

        rooms = dungeon.get("rooms", {})
        current_room = rooms.get(state.current_room_id)
        if current_room is None:
            return ValidationResult.fail("Current room does not exist.")

        if not current_room.get("rest_allowed", False):
            return ValidationResult.fail("Rest is not allowed in this room.")

        if state.dungeon_state.has_rested_in(state.current_room_id):
            return ValidationResult.fail("This room has already been used for resting.")

        return ValidationResult.ok()

    def _validate_attack_action(
        self, action: Action, state: EncounterState, actor: Entity
    ) -> ValidationResult:
        attack_id = action.parameters.get("attack_id")
        if not attack_id:
            return ValidationResult.fail("Attack action requires an attack_id.")

        if attack_id not in actor.known_attacks:
            return ValidationResult.fail("Actor does not know this attack.")

        if self.data_loader.get_attack(attack_id) is None:
            return ValidationResult.fail("Attack definition not found.")

        if not action.target_id:
            return ValidationResult.fail("Attack action requires a target.")

        target = state.get_entity(action.target_id)
        if target is None:
            return ValidationResult.fail("Target does not exist in this encounter.")

        if not target.is_alive():
            return ValidationResult.fail("Target is already defeated.")

        return ValidationResult.ok()

    def _validate_cast_spell_action(
        self, action: Action, state: EncounterState, actor: Entity
    ) -> ValidationResult:
        spell_id = action.parameters.get("spell_id")
        if not spell_id:
            return ValidationResult.fail("Cast spell action requires a spell_id.")

        if spell_id not in actor.known_spells:
            return ValidationResult.fail("Actor does not know this spell.")

        spell = self.data_loader.get_spell(spell_id)
        if spell is None:
            return ValidationResult.fail("Spell definition not found.")

        if actor.spell_slots.current <= 0:
            return ValidationResult.fail("No spell slots available.")

        target_rule = spell.get("target")
        if target_rule in {"enemy", "ally", "self"} and not action.target_id:
            return ValidationResult.fail("Spell requires a single target.")

        if target_rule in {"enemies", "allies"} and action.target_id:
            return ValidationResult.fail("AoE spell should not specify a single target.")

        if action.target_id:
            target = state.get_entity(action.target_id)
            if target is None:
                return ValidationResult.fail("Target does not exist in this encounter.")
            if not target.is_alive():
                return ValidationResult.fail("Target is already defeated.")

        return ValidationResult.ok()
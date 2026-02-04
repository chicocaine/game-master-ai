from typing import Optional

from models.actions import Action
from models.states import GlobalGameState, EncounterState, GameMode


class ActionValidationError(Exception):
    """Raised when an action is invalid."""
    pass


# -----------------------------
# Public API
# -----------------------------

def validate_action(
    action: Action,
    global_state: GlobalGameState,
    encounter_state: Optional[EncounterState] = None
) -> None:
    """
    Validates an action against the current game state.
    Raises ActionValidationError if invalid.
    """

    if global_state.game_mode == GameMode.EXPLORATION:
        _validate_exploration_action(action, global_state)

    elif global_state.game_mode == GameMode.ENCOUNTER:
        if encounter_state is None:
            raise ActionValidationError("Encounter state is missing.")
        _validate_encounter_action(action, encounter_state)

    elif global_state.game_mode == GameMode.GAME_OVER:
        raise ActionValidationError("Game is already over.")

    else:
        raise ActionValidationError("Unknown game mode.")


# -----------------------------
# Exploration Validation
# -----------------------------

def _validate_exploration_action(
    action: Action,
    global_state: GlobalGameState
) -> None:

    if action.action_type == "move":
        if not action.target_id:
            raise ActionValidationError("Move action requires a target room.")

        # NOTE: actual graph connectivity check happens in exploration logic
        return

    if action.action_type == "rest":
        rest_type = action.parameters.get("rest_type")
        if rest_type not in ("short", "long"):
            raise ActionValidationError("Invalid rest type.")
        return

    if action.action_type == "explore":
        return

    raise ActionValidationError(
        f"Action '{action.action_type}' is not valid in exploration mode."
    )


# -----------------------------
# Encounter Validation
# -----------------------------

def _validate_encounter_action(
    action: Action,
    encounter_state: EncounterState
) -> None:

    if action.actor_id != encounter_state.active_entity_id:
        raise ActionValidationError("It is not this entity's turn.")

    actor = encounter_state.get_entity(action.actor_id)
    if actor is None:
        raise ActionValidationError("Acting entity does not exist.")

    if actor["hp"] <= 0:
        raise ActionValidationError("Defeated entities cannot act.")

    if action.action_type == "attack":
        _validate_attack(action, encounter_state)
        return

    if action.action_type == "cast_spell":
        _validate_cast_spell(action, encounter_state)
        return

    if action.action_type == "end_turn":
        return

    raise ActionValidationError(
        f"Action '{action.action_type}' is not valid in encounter mode."
    )


def _validate_attack(action: Action, encounter_state: EncounterState) -> None:
    if not action.target_id:
        raise ActionValidationError("Attack requires a target.")

    target = encounter_state.get_entity(action.target_id)
    if target is None:
        raise ActionValidationError("Target does not exist.")

    if target["hp"] <= 0:
        raise ActionValidationError("Target is already defeated.")

    attack_id = action.parameters.get("attack_id")
    if not attack_id:
        raise ActionValidationError("Attack requires an attack_id.")


def _validate_cast_spell(action: Action, encounter_state: EncounterState) -> None:
    spell_id = action.parameters.get("spell_id")
    if not spell_id:
        raise ActionValidationError("Cast spell requires spell_id.")

    actor = encounter_state.get_entity(action.actor_id)
    slots = actor.get("spell_slots", {})

    if slots.get("current", 0) <= 0:
        raise ActionValidationError("No spell slots remaining.")

    # AoE spells may have no target
    if action.target_id:
        target = encounter_state.get_entity(action.target_id)
        if target is None:
            raise ActionValidationError("Target does not exist.")
        if target["hp"] <= 0:
            raise ActionValidationError("Target is already defeated.")

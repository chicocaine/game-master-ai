from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Dict, Iterable, List, Optional, Set

from core.actions import Action
from core.enums import ActionType, GameState
from core.models.dungeon import Encounter, Room
from core.states.session import GameSessionState, find_room, first_uncleared_encounter


GLOBAL_ACTIONS: Set[ActionType] = {
	ActionType.ABANDON,
	ActionType.QUERY,
	ActionType.CONVERSE,
}


STATE_ACTIONS: Dict[GameState, Set[ActionType]] = {
	GameState.PREGAME: {
		ActionType.CREATE_PLAYER,
		ActionType.REMOVE_PLAYER,
		ActionType.CHOOSE_DUNGEON,
		ActionType.START,
	},
	GameState.EXPLORATION: {
		ActionType.MOVE,
		ActionType.EXPLORE,
		ActionType.REST,
	},
	GameState.ENCOUNTER: {
		ActionType.ATTACK,
		ActionType.CAST_SPELL,
		ActionType.END_TURN,
	},
	GameState.POSTGAME: {
		ActionType.FINISH,
	},
}


@dataclass(frozen=True)
class RuleViolation:
	code: str
	message: str
	field: str = ""
	context: Dict[str, object] = dataclass_field(default_factory=dict)


def legal_actions_for_state(state: GameState) -> Set[ActionType]:
	return set(STATE_ACTIONS.get(state, set())) | GLOBAL_ACTIONS


def is_action_legal_for_state(state: GameState, action_type: ActionType) -> bool:
	return action_type in legal_actions_for_state(state)


def validate_action_legality(session: GameSessionState, action: Action) -> List[RuleViolation]:
	if is_action_legal_for_state(session.state, action.type):
		return []
	return [
		RuleViolation(
			code="illegal_action_for_state",
			message=f"Action '{action.type.value}' is not legal in state '{session.state.value}'",
			field="type",
			context={
				"state": session.state.value,
				"action_type": action.type.value,
				"legal_actions": sorted(item.value for item in legal_actions_for_state(session.state)),
			},
		)
	]


def can_start_session(session: GameSessionState) -> List[RuleViolation]:
	violations: List[RuleViolation] = []
	if not session.party:
		violations.append(
			RuleViolation(
				code="start_requires_party",
				message="Cannot start without at least one party member",
			)
		)
	if session.dungeon is None:
		violations.append(
			RuleViolation(
				code="start_requires_dungeon",
				message="Cannot start without selecting a dungeon",
			)
		)
	return violations


def can_move_to_room(session: GameSessionState, destination_room_id: str) -> List[RuleViolation]:
	if session.dungeon is None:
		return [RuleViolation(code="dungeon_not_selected", message="Dungeon not selected")]

	current_room = find_room(session.dungeon, session.exploration.current_room_id)
	destination_room = find_room(session.dungeon, destination_room_id)
	violations: List[RuleViolation] = []

	if current_room is None:
		violations.append(RuleViolation(code="current_room_not_found", message="Current room not found"))
		return violations

	if destination_room is None:
		violations.append(RuleViolation(code="destination_room_not_found", message="Destination room not found"))
		return violations

	if destination_room_id not in current_room.connections:
		violations.append(
			RuleViolation(
				code="destination_not_connected",
				message="Destination room is not connected",
				field="destination_room_id",
			)
		)

	if not current_room.is_cleared:
		violations.append(
			RuleViolation(
				code="current_room_not_cleared",
				message="Cannot move while current room is not cleared",
			)
		)

	return violations


def active_uncleared_encounter(session: GameSessionState) -> Optional[Encounter]:
	if session.dungeon is None:
		return None
	room = find_room(session.dungeon, session.exploration.current_room_id)
	if room is None:
		return None
	return first_uncleared_encounter(room)


def should_transition_to_encounter(session: GameSessionState) -> bool:
	return active_uncleared_encounter(session) is not None


def is_room_completion_target(session: GameSessionState, room: Room) -> bool:
	if session.dungeon is None:
		return False
	return room.id == session.dungeon.end_room and room.is_cleared


def should_transition_to_postgame(session: GameSessionState) -> bool:
	if session.dungeon is None:
		return False
	if session.exploration.current_room_id != session.dungeon.end_room:
		return False

	room = find_room(session.dungeon, session.dungeon.end_room)
	if room is None:
		return False
	return is_room_completion_target(session, room)


def normalize_violations(violations: Iterable[RuleViolation]) -> List[str]:
	return [violation.message for violation in violations]

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Dict, Iterable, List, Optional, Set

from core.actions import Action
from core.enums import ActionType, GameState, RestType
from core.models.dungeon import Encounter, Room
from core.models.enemy import Enemy
from core.models.player import Player
from core.states.session import (
	GameSessionState,
	find_player_by_instance_id,
	find_room,
	first_uncleared_encounter,
	get_active_encounter,
)


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


def validate_rest_constraints(session: GameSessionState, rest_type_raw: str) -> List[RuleViolation]:
	if session.dungeon is None:
		return [RuleViolation(code="dungeon_not_selected", message="Dungeon not selected")]

	room = find_room(session.dungeon, session.exploration.current_room_id)
	if room is None:
		return [RuleViolation(code="current_room_not_found", message="Current room not found")]

	violations: List[RuleViolation] = []
	rest_type_value = rest_type_raw.strip()
	if not rest_type_value:
		violations.append(RuleViolation(code="missing_rest_type", message="Missing rest_type", field="rest_type"))
		return violations

	try:
		rest_type = RestType(rest_type_value)
	except ValueError:
		violations.append(RuleViolation(code="invalid_rest_type", message="Invalid rest_type", field="rest_type"))
		return violations

	if room.is_rested:
		violations.append(RuleViolation(code="room_already_rested", message="Room already rested"))

	if rest_type not in room.allowed_rests:
		violations.append(RuleViolation(code="rest_not_allowed", message="Rest type not allowed in this room"))

	return violations


def validate_actor_turn(session: GameSessionState, actor_instance_id: str) -> List[RuleViolation]:
	if not session.encounter.turn_order:
		return [RuleViolation(code="no_active_turn_order", message="No active turn order")]
	if session.encounter.current_turn_index >= len(session.encounter.turn_order):
		return [RuleViolation(code="invalid_turn_index", message="Encounter turn index out of bounds")]

	active_actor = session.encounter.turn_order[session.encounter.current_turn_index]
	if active_actor != actor_instance_id:
		return [
			RuleViolation(
				code="not_actor_turn",
				message="Action is not legal outside the actor's turn",
				field="actor_instance_id",
				context={"active_actor_instance_id": active_actor},
			)
		]
	return []


def normalize_target_ids(raw: object) -> List[str]:
	if isinstance(raw, str):
		return [raw]
	if isinstance(raw, list):
		return [str(item) for item in raw]
	return []


def resolve_actor(session: GameSessionState, actor_instance_id: str) -> Optional[Player | Enemy]:
	encounter = get_active_encounter(session)
	actor_player = find_player_by_instance_id(session, actor_instance_id)
	if actor_player is not None:
		return actor_player
	if encounter is None:
		return None
	for enemy in encounter.enemies:
		if enemy.enemy_instance_id == actor_instance_id:
			return enemy
	return None


def validate_encounter_target_ids(session: GameSessionState, target_ids: List[str]) -> List[RuleViolation]:
	encounter = get_active_encounter(session)
	if encounter is None:
		return [RuleViolation(code="no_active_encounter", message="No active encounter")]

	valid_ids = {player.player_instance_id for player in session.party}
	valid_ids.update(enemy.enemy_instance_id for enemy in encounter.enemies)

	violations: List[RuleViolation] = []
	for target_id in target_ids:
		if target_id not in valid_ids:
			violations.append(
				RuleViolation(
					code="unknown_target",
					message=f"Unknown target '{target_id}'",
					field="target_instance_ids",
				)
			)
	return violations


def validate_attack_rules(session: GameSessionState, action: Action) -> List[RuleViolation]:
	encounter = get_active_encounter(session)
	if encounter is None:
		return [RuleViolation(code="no_active_encounter", message="No active encounter")]

	violations: List[RuleViolation] = []
	violations.extend(validate_actor_turn(session, action.actor_instance_id))

	actor = resolve_actor(session, action.actor_instance_id)
	if actor is None:
		violations.append(RuleViolation(code="actor_not_found", message="Actor not found", field="actor_instance_id"))
		return violations
	if actor.hp <= 0:
		violations.append(RuleViolation(code="actor_defeated", message="Defeated actor cannot act"))

	attack_id = str(action.parameters.get("attack_id", "")).strip()
	if attack_id:
		known_attack_ids = {attack.id for attack in actor.merged_attacks}
		if attack_id not in known_attack_ids:
			violations.append(
				RuleViolation(
					code="unknown_attack",
					message=f"Unknown attack '{attack_id}'",
					field="attack_id",
				)
			)

	target_ids = normalize_target_ids(action.parameters.get("target_instance_ids", []))
	if not target_ids:
		violations.append(
			RuleViolation(
				code="missing_targets",
				message="Missing targets",
				field="target_instance_ids",
			)
		)
		return violations

	violations.extend(validate_encounter_target_ids(session, target_ids))
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

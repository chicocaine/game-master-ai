from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Dict, List

from core.actions import Action, validate_action
from core.enums import ActionType
from core.rules import (
	RuleViolation,
	can_move_to_room,
	can_start_session,
	resolve_actor,
	validate_action_legality,
	validate_actor_turn,
	validate_attack_rules,
	validate_rest_constraints,
)
from core.states.session import (
	GameSessionState,
	alive_enemies,
	alive_players,
	get_active_encounter,
)


@dataclass(frozen=True)
class ValidationIssue:
	code: str
	message: str
	field: str = ""
	context: Dict[str, object] = dataclass_field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
	is_valid: bool
	issues: List[ValidationIssue] = dataclass_field(default_factory=list)

	@property
	def errors(self) -> List[str]:
		return [issue.message for issue in self.issues]


def _issue_from_rule(violation: RuleViolation) -> ValidationIssue:
	return ValidationIssue(
		code=violation.code,
		message=violation.message,
		field=violation.field,
		context=violation.context,
	)


def _add_action_schema_issues(action: Action, issues: List[ValidationIssue]) -> None:
	for message in validate_action(action):
		issues.append(ValidationIssue(code="invalid_action_parameters", message=message))


def _validate_create_player(action: Action) -> List[ValidationIssue]:
	issues: List[ValidationIssue] = []
	for field_name in ("name", "description", "race", "archetype"):
		if not str(action.parameters.get(field_name, "")).strip():
			issues.append(
				ValidationIssue(
					code=f"missing_{field_name}",
					message=f"Missing {field_name}",
					field=field_name,
				)
			)

	weapons_raw = action.parameters.get("weapons")
	if not isinstance(weapons_raw, list):
		issues.append(
			ValidationIssue(
				code="invalid_weapons",
				message="Weapons must be a list",
				field="weapons",
			)
		)
		return issues

	if not weapons_raw:
		issues.append(
			ValidationIssue(
				code="missing_weapons",
				message="Missing weapons",
				field="weapons",
			)
		)
		return issues

	for item in weapons_raw:
		if not str(item).strip():
			issues.append(
				ValidationIssue(
					code="invalid_weapon_id",
					message="Weapon ids must be non-blank strings",
					field="weapons",
				)
			)
			break
	return issues


def _validate_remove_player(action: Action) -> List[ValidationIssue]:
	issues: List[ValidationIssue] = []
	if not str(action.parameters.get("player_instance_id", "")).strip():
		issues.append(
			ValidationIssue(
				code="missing_player_instance_id",
				message="Missing player_instance_id",
				field="player_instance_id",
			)
		)
	return issues


def _validate_choose_dungeon(action: Action) -> List[ValidationIssue]:
	issues: List[ValidationIssue] = []
	if not str(action.parameters.get("dungeon_id", "")).strip():
		issues.append(
			ValidationIssue(
				code="missing_dungeon_id",
				message="Missing dungeon_id",
				field="dungeon_id",
			)
		)
	return issues


def _validate_start(session: GameSessionState) -> List[ValidationIssue]:
	return [_issue_from_rule(item) for item in can_start_session(session)]


def _validate_move(session: GameSessionState, action: Action) -> List[ValidationIssue]:
	destination_room_id = str(action.parameters.get("destination_room_id", "")).strip()
	if not destination_room_id:
		return [
			ValidationIssue(
				code="missing_destination_room_id",
				message="Missing destination_room_id",
				field="destination_room_id",
			)
		]
	return [_issue_from_rule(item) for item in can_move_to_room(session, destination_room_id)]


def _validate_rest(session: GameSessionState, action: Action) -> List[ValidationIssue]:
	rest_type_raw = str(action.parameters.get("rest_type", "")).strip()
	return [_issue_from_rule(item) for item in validate_rest_constraints(session, rest_type_raw)]


def _validate_attack(session: GameSessionState, action: Action) -> List[ValidationIssue]:
	return [_issue_from_rule(item) for item in validate_attack_rules(session, action)]


def _validate_cast_spell(session: GameSessionState, action: Action) -> List[ValidationIssue]:
	issues = _validate_attack(session, action)
	if issues:
		return issues

	actor = resolve_actor(session, action.actor_instance_id)
	if actor is None:
		return [ValidationIssue(code="actor_not_found", message="Actor not found", field="actor_instance_id")]

	spell_id = str(action.parameters.get("spell_id", "")).strip()
	if not spell_id:
		return [ValidationIssue(code="missing_spell_id", message="Missing spell_id", field="spell_id")]

	matching_spell = next((spell for spell in actor.merged_spells if spell.id == spell_id), None)
	if matching_spell is None:
		return [ValidationIssue(code="unknown_spell", message=f"Unknown spell '{spell_id}'", field="spell_id")]

	if actor.spell_slots < matching_spell.spell_cost:
		return [
			ValidationIssue(
				code="insufficient_spell_slots",
				message="Not enough spell slots",
				field="spell_id",
				context={
					"available_spell_slots": actor.spell_slots,
					"required_spell_slots": matching_spell.spell_cost,
				},
			)
		]

	return []


def _validate_end_turn(session: GameSessionState, action: Action) -> List[ValidationIssue]:
	return [_issue_from_rule(item) for item in validate_actor_turn(session, action.actor_instance_id)]


def validate_action_for_state(session: GameSessionState, action: Action) -> List[str]:
	return validate_action_with_details(session, action).errors


def validate_action_with_details(session: GameSessionState, action: Action) -> ValidationResult:
	issues: List[ValidationIssue] = []

	issues.extend(_issue_from_rule(item) for item in validate_action_legality(session, action))
	_add_action_schema_issues(action, issues)

	if action.type == ActionType.CREATE_PLAYER:
		issues.extend(_validate_create_player(action))
	elif action.type == ActionType.REMOVE_PLAYER:
		issues.extend(_validate_remove_player(action))
	elif action.type == ActionType.CHOOSE_DUNGEON:
		issues.extend(_validate_choose_dungeon(action))
	elif action.type == ActionType.START:
		issues.extend(_validate_start(session))
	elif action.type == ActionType.MOVE:
		issues.extend(_validate_move(session, action))
	elif action.type == ActionType.REST:
		issues.extend(_validate_rest(session, action))
	elif action.type == ActionType.ATTACK:
		issues.extend(_validate_attack(session, action))
	elif action.type == ActionType.CAST_SPELL:
		issues.extend(_validate_cast_spell(session, action))
	elif action.type == ActionType.END_TURN:
		issues.extend(_validate_end_turn(session, action))

	return ValidationResult(is_valid=not issues, issues=issues)


def validate_encounter_participants_alive(session: GameSessionState) -> ValidationResult:
	encounter = get_active_encounter(session)
	if encounter is None:
		return ValidationResult(
			is_valid=False,
			issues=[ValidationIssue(code="no_active_encounter", message="No active encounter")],
		)

	if not alive_players(session.party):
		return ValidationResult(
			is_valid=False,
			issues=[ValidationIssue(code="party_defeated", message="All party members are defeated")],
		)

	if not alive_enemies(encounter):
		return ValidationResult(
			is_valid=False,
			issues=[ValidationIssue(code="encounter_cleared", message="All enemies are defeated")],
		)

	return ValidationResult(is_valid=True, issues=[])

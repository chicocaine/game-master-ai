"""Intent-to-action mapping logic."""

from dataclasses import dataclass, field
from typing import List, Optional

from models.actions import (
	Action,
	ActionType,
	AttackAction,
	CastSpellAction,
	EndTurnAction,
	ExploreAction,
	MoveAction,
	RestAction,
	RestType,
)
from models.data_loader import DataLoader
from models.entities import Entity, EntityType
from models.states import EncounterState, GlobalGameState

from agent.parser import ParsedIntent


@dataclass
class ActionMappingResult:
	"""Encapsulates action mapping results."""

	action: Optional[Action] = None
	errors: List[str] = field(default_factory=list)
	needs_clarification: bool = False
	clarification_prompt: Optional[str] = None

	@classmethod
	def ok(cls, action: Action) -> "ActionMappingResult":
		return cls(action=action)

	@classmethod
	def fail(cls, *errors: str) -> "ActionMappingResult":
		return cls(action=None, errors=list(errors))

	@classmethod
	def clarify(cls, prompt: str, *errors: str) -> "ActionMappingResult":
		return cls(
			action=None,
			errors=list(errors),
			needs_clarification=True,
			clarification_prompt=prompt,
		)


class ActionMapper:
	"""Maps parsed intents into concrete Action objects."""

	def __init__(self, data_loader: Optional[DataLoader] = None) -> None:
		self.data_loader = data_loader

	def map_intent(
		self,
		parsed: ParsedIntent,
		actor: Optional[Entity],
		global_state: Optional[GlobalGameState] = None,
		encounter_state: Optional[EncounterState] = None,
	) -> ActionMappingResult:
		if parsed.intent == "unknown":
			return ActionMappingResult.clarify(
				"I didn't understand that. Try move, attack, cast a spell, rest, explore, or end turn.",
				"Unknown intent.",
			)

		if parsed.intent == ActionType.MOVE.value:
			return self._map_move(parsed, actor, global_state)

		if parsed.intent == ActionType.ATTACK.value:
			return self._map_attack(parsed, actor, encounter_state)

		if parsed.intent == ActionType.CAST_SPELL.value:
			return self._map_cast_spell(parsed, actor, encounter_state)

		if parsed.intent == ActionType.REST.value:
			return self._map_rest(parsed, actor)

		if parsed.intent == ActionType.END_TURN.value:
			if not actor:
				return ActionMappingResult.fail("Actor is required to end turn.")
			return ActionMappingResult.ok(EndTurnAction(actor.entity_id))

		if parsed.intent == ActionType.EXPLORE.value:
			if not actor:
				return ActionMappingResult.fail("Actor is required to explore.")
			return ActionMappingResult.ok(ExploreAction(actor.entity_id))

		return ActionMappingResult.fail(f"Unsupported intent: {parsed.intent}")

	def _map_move(
		self,
		parsed: ParsedIntent,
		actor: Optional[Entity],
		global_state: Optional[GlobalGameState],
	) -> ActionMappingResult:
		if not actor:
			return ActionMappingResult.fail("Actor is required to move.")

		target_room_id = parsed.room_id
		if target_room_id is None:
			target_room_id = self._infer_single_connected_room(global_state)

		if target_room_id is None:
			return ActionMappingResult.clarify(
				"Where do you want to go?",
				"Move target room is missing.",
			)

		return ActionMappingResult.ok(MoveAction(actor.entity_id, target_room_id))

	def _map_attack(
		self,
		parsed: ParsedIntent,
		actor: Optional[Entity],
		encounter_state: Optional[EncounterState],
	) -> ActionMappingResult:
		if not actor:
			return ActionMappingResult.fail("Actor is required to attack.")

		attack_id = parsed.attack_id
		if attack_id is None and len(actor.known_attacks) == 1:
			attack_id = actor.known_attacks[0]

		target_id = parsed.target_id
		if target_id is None:
			target_id = self._infer_single_enemy(encounter_state)

		if attack_id is None:
			return ActionMappingResult.clarify(
				"Which attack do you want to use?",
				"Attack id is missing.",
			)

		if target_id is None:
			return ActionMappingResult.clarify(
				"Which target do you want to attack?",
				"Attack target is missing.",
			)

		return ActionMappingResult.ok(AttackAction(actor.entity_id, target_id, attack_id))

	def _map_cast_spell(
		self,
		parsed: ParsedIntent,
		actor: Optional[Entity],
		encounter_state: Optional[EncounterState],
	) -> ActionMappingResult:
		if not actor:
			return ActionMappingResult.fail("Actor is required to cast a spell.")

		spell_id = parsed.spell_id
		if spell_id is None and len(actor.known_spells) == 1:
			spell_id = actor.known_spells[0]

		if spell_id is None:
			return ActionMappingResult.clarify(
				"Which spell do you want to cast?",
				"Spell id is missing.",
			)

		target_id = parsed.target_id
		target_rule = self._get_spell_target_rule(spell_id)

		if target_rule in {"enemies", "allies"}:
			target_id = None
		elif target_rule == "self":
			target_id = actor.entity_id
		elif target_id is None:
			target_id = self._infer_spell_target(actor, encounter_state, target_rule)

		if target_rule in {"enemy", "ally"} and target_id is None:
			return ActionMappingResult.clarify(
				"Which target should the spell affect?",
				"Spell target is missing.",
			)

		return ActionMappingResult.ok(CastSpellAction(actor.entity_id, spell_id, target_id))

	def _map_rest(self, parsed: ParsedIntent, actor: Optional[Entity]) -> ActionMappingResult:
		if not actor:
			return ActionMappingResult.fail("Actor is required to rest.")

		rest_type = parsed.rest_type or RestType.SHORT.value
		return ActionMappingResult.ok(RestAction(actor.entity_id, RestType(rest_type)))

	def _infer_single_enemy(self, encounter_state: Optional[EncounterState]) -> Optional[str]:
		if encounter_state is None:
			return None
		living_enemies = encounter_state.get_living_enemies()
		if len(living_enemies) == 1:
			return living_enemies[0].entity_id
		return None

	def _infer_single_connected_room(
		self, global_state: Optional[GlobalGameState]
	) -> Optional[str]:
		if not self.data_loader or not global_state:
			return None
		dungeon = self.data_loader.get_dungeon(global_state.current_dungeon_id)
		if not dungeon:
			return None
		rooms = dungeon.get("rooms", {})
		current_room = rooms.get(global_state.current_room_id)
		if not current_room:
			return None
		connections = current_room.get("connections", [])
		if len(connections) == 1:
			return connections[0]
		return None

	def _get_spell_target_rule(self, spell_id: str) -> Optional[str]:
		if not self.data_loader:
			return None
		spell = self.data_loader.get_spell(spell_id)
		if not spell:
			return None
		return spell.get("target")

	def _infer_spell_target(
		self,
		actor: Entity,
		encounter_state: Optional[EncounterState],
		target_rule: Optional[str],
	) -> Optional[str]:
		if encounter_state is None or target_rule is None:
			return None

		if target_rule == "enemy":
			return self._infer_single_enemy(encounter_state)

		if target_rule == "ally":
			living_allies = self._get_living_allies(actor, encounter_state)
			if len(living_allies) == 1:
				return living_allies[0].entity_id

		return None

	@staticmethod
	def _get_living_allies(actor: Entity, encounter_state: EncounterState) -> List[Entity]:
		if actor.entity_type == EntityType.PLAYER:
			return encounter_state.get_living_players()
		return encounter_state.get_living_enemies()


def map_intent_to_action(
	parsed: ParsedIntent,
	actor: Optional[Entity],
	global_state: Optional[GlobalGameState] = None,
	encounter_state: Optional[EncounterState] = None,
	data_loader: Optional[DataLoader] = None,
) -> ActionMappingResult:
	"""Convenience function for mapping intents to actions."""
	mapper = ActionMapper(data_loader=data_loader)
	return mapper.map_intent(
		parsed=parsed,
		actor=actor,
		global_state=global_state,
		encounter_state=encounter_state,
	)

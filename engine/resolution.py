"""Resolution engine for applying actions and effects."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from models.actions import Action, ActionType, RestType
from models.entities import Entity, StatusEffect
from models.states import GlobalGameState, EncounterState, GameMode
from models.data_loader import DataLoader
from utils.dice import roll_d20, roll_dice, RollResult
from utils.session_logger import SessionLogger


@dataclass
class ResolutionResult:
	"""Encapsulates the outcome of resolving an action."""
	success: bool
	narration: str
	details: Dict[str, Any] = field(default_factory=dict)


class ResolutionEngine:
	"""Applies game rules to resolve actions and effects."""

	def __init__(self, data_loader: DataLoader):
		self.data_loader = data_loader

	def resolve_action(
		self,
		action: Action,
		global_state: GlobalGameState,
		encounter_state: Optional[EncounterState] = None,
		logger: Optional[SessionLogger] = None,
	) -> ResolutionResult:
		"""Resolve an action and mutate the relevant state."""
		if global_state.game_mode == GameMode.EXPLORATION:
			if action.action_type == ActionType.REST:
				return self._resolve_rest(action, global_state, logger)

			return ResolutionResult(
				success=False,
				narration="Exploration actions are resolved in the exploration engine.",
			)

		if global_state.game_mode != GameMode.ENCOUNTER or encounter_state is None:
			return ResolutionResult(
				success=False,
				narration="Encounter state is required to resolve combat actions.",
			)

		if action.action_type == ActionType.ATTACK:
			return self._resolve_attack(action, encounter_state, logger)

		if action.action_type == ActionType.CAST_SPELL:
			return self._resolve_cast_spell(action, encounter_state, logger)

		if action.action_type == ActionType.END_TURN:
			encounter_state.advance_turn()
			return ResolutionResult(
				success=True,
				narration="Turn ended.",
				details={"round": encounter_state.round},
			)

		return ResolutionResult(
			success=False,
			narration=f"Unsupported action type: {action.action_type.value}.",
		)

	def resolve_start_of_turn(
		self,
		entity: Entity,
		encounter_state: EncounterState,
		logger: Optional[SessionLogger] = None,
	) -> Dict[str, Any]:
		"""Resolve start-of-turn effects like poison or burn."""
		triggered: List[Dict[str, Any]] = []
		for effect in list(entity.status_effects):
			if effect.effect_type in {"poisoned", "burned"}:
				damage = max(0, effect.magnitude)
				applied = entity.take_damage(damage)
				triggered.append(
					{
						"effect_type": effect.effect_type,
						"damage_applied": applied,
						"duration_remaining": max(0, effect.duration - 1),
					}
				)
				if logger:
					logger.log_status_effect_triggered(
						entity_id=entity.entity_id,
						effect_type=effect.effect_type,
						damage_applied=applied,
						duration_remaining=max(0, effect.duration - 1),
					)

		entity.decrement_status_effects()

		return {"entity_id": entity.entity_id, "triggered": triggered}

	def _resolve_attack(
		self,
		action: Action,
		state: EncounterState,
		logger: Optional[SessionLogger],
	) -> ResolutionResult:
		actor = state.get_entity(action.actor_id)
		target = state.get_entity(action.target_id or "")
		attack_id = action.parameters.get("attack_id")

		if actor is None or target is None:
			return ResolutionResult(False, "Attack failed: invalid actor or target.")

		attack = self.data_loader.get_attack(attack_id)
		if attack is None:
			return ResolutionResult(False, "Attack failed: attack data not found.")

		roll = roll_d20()
		to_hit_modifier = attack.get("to_hit_modifier", 0)
		total_to_hit = roll + actor.get_attack_modifier() + to_hit_modifier
		target_ac = target.ac + target.get_ac_modifier()
		hit = total_to_hit >= target_ac

		details: Dict[str, Any] = {
			"attack_id": attack_id,
			"roll": roll,
			"to_hit_modifier": to_hit_modifier,
			"total_to_hit": total_to_hit,
			"target_ac": target_ac,
			"hit": hit,
		}

		if hit:
			damage_roll = roll_dice(attack["damage"])
			applied = target.take_damage(damage_roll.total)
			details.update(
				{
					"damage_roll": _roll_to_dict(damage_roll),
					"damage_applied": applied,
					"target_hp": target.hp,
				}
			)

			status_payload = attack.get("status_effect")
			if status_payload:
				self._apply_status_effect(target, status_payload, actor.entity_id, logger)

			narration = (
				f"{actor.name} hits {target.name} with {attack['name']} "
				f"for {applied} damage."
			)
		else:
			narration = f"{actor.name} misses {target.name} with {attack['name']}."

		if logger and target.hp == 0:
			logger.log_entity_died(
				entity_id=target.entity_id,
				name=target.name,
				final_hp=target.hp,
				killed_by=actor.entity_id,
			)

		return ResolutionResult(True, narration, details)

	def _resolve_cast_spell(
		self,
		action: Action,
		state: EncounterState,
		logger: Optional[SessionLogger],
	) -> ResolutionResult:
		actor = state.get_entity(action.actor_id)
		if actor is None:
			return ResolutionResult(False, "Spell failed: invalid actor.")

		spell_id = action.parameters.get("spell_id")
		spell = self.data_loader.get_spell(spell_id)
		if spell is None:
			return ResolutionResult(False, "Spell failed: spell data not found.")

		if not actor.spell_slots.use_slot():
			return ResolutionResult(False, "Spell failed: no spell slots available.")

		targets = self._select_spell_targets(spell, action.target_id, state, actor)
		if not targets:
			return ResolutionResult(False, "Spell failed: no valid targets.")

		details: Dict[str, Any] = {"spell_id": spell_id, "targets": []}
		narration_targets = ", ".join(t.name for t in targets)
		narration = f"{actor.name} casts {spell['name']} on {narration_targets}."

		if spell["category"] == "damage":
			damage_roll = roll_dice(spell["damage"])
			for target in targets:
				applied = target.take_damage(damage_roll.total)
				details["targets"].append(
					{
						"target_id": target.entity_id,
						"damage_roll": _roll_to_dict(damage_roll),
						"damage_applied": applied,
						"target_hp": target.hp,
					}
				)
				if logger and target.hp == 0:
					logger.log_entity_died(
						entity_id=target.entity_id,
						name=target.name,
						final_hp=target.hp,
						killed_by=actor.entity_id,
					)

		elif spell["category"] == "heal":
			heal_roll = roll_dice(spell["heal"])
			for target in targets:
				applied = target.heal(heal_roll.total)
				details["targets"].append(
					{
						"target_id": target.entity_id,
						"heal_roll": _roll_to_dict(heal_roll),
						"healing_applied": applied,
						"target_hp": target.hp,
					}
				)

		elif spell["category"] == "status":
			status_payload = spell.get("status_effect")
			if not status_payload:
				return ResolutionResult(False, "Spell failed: missing status effect.")
			for target in targets:
				self._apply_status_effect(target, status_payload, actor.entity_id, logger)
				details["targets"].append(
					{
						"target_id": target.entity_id,
						"status_effect": status_payload,
					}
				)
		else:
			return ResolutionResult(False, f"Spell failed: unknown category {spell['category']}.")

		return ResolutionResult(True, narration, details)

	def _resolve_rest(
		self,
		action: Action,
		state: GlobalGameState,
		logger: Optional[SessionLogger],
	) -> ResolutionResult:
		rest_type_value = action.parameters.get("rest_type")
		rest_type = RestType(rest_type_value)

		details = {"rest_type": rest_type.value, "players": []}
		for player in state.players:
			before_hp = player.hp
			before_slots = player.spell_slots.current

			if rest_type == RestType.SHORT:
				heal_amount = max(1, int(player.max_hp * 0.25))
				player.heal(heal_amount)
				if player.spell_slots.max > 0:
					player.spell_slots.restore(1)
			else:
				player.hp = player.max_hp
				player.spell_slots.restore_all()

			details["players"].append(
				{
					"entity_id": player.entity_id,
					"hp_before": before_hp,
					"hp_after": player.hp,
					"spell_slots_before": before_slots,
					"spell_slots_after": player.spell_slots.current,
				}
			)

		state.dungeon_state.mark_rested(state.current_room_id)

		if logger:
			logger.log_rest_completed(
				rest_type=rest_type.value,
				room_id=state.current_room_id,
				player_states=details["players"],
			)

		narration = "The party takes a short rest." if rest_type == RestType.SHORT else "The party takes a long rest."
		return ResolutionResult(True, narration, details)

	def _select_spell_targets(
		self,
		spell: Dict[str, Any],
		target_id: Optional[str],
		state: EncounterState,
		actor: Entity,
	) -> List[Entity]:
		target_rule = spell.get("target")
		if target_rule == "self":
			return [actor]

		if target_rule == "enemy":
			target = state.get_entity(target_id or "")
			return [target] if target else []

		if target_rule == "ally":
			target = state.get_entity(target_id or "")
			return [target] if target else []

		if target_rule == "enemies":
			return state.get_living_enemies()

		if target_rule == "allies":
			return state.get_living_players()

		return []

	def _apply_status_effect(
		self,
		target: Entity,
		payload: Dict[str, Any],
		source_id: Optional[str],
		logger: Optional[SessionLogger],
	) -> None:
		effect = StatusEffect(
			effect_type=payload.get("type", "unknown"),
			duration=payload.get("duration", 1),
			magnitude=payload.get("magnitude", 1),
			source_id=source_id,
		)
		target.remove_status_effect(effect.effect_type)
		target.add_status_effect(effect)

		if logger:
			logger.log_status_effect_applied(
				entity_id=target.entity_id,
				effect_type=effect.effect_type,
				duration=effect.duration,
				magnitude=effect.magnitude,
				source_id=source_id,
			)


def _roll_to_dict(roll: RollResult) -> Dict[str, Any]:
	return {
		"expression": roll.expression,
		"rolls": roll.rolls,
		"modifier": roll.modifier,
		"total": roll.total,
	}

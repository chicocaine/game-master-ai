from dataclasses import dataclass
from typing import Any, List, Optional

from core.enums import SpellType, DamageType
from models.status_effect import StatusEffect


def _parse_spell_type(spell_type: Any) -> SpellType:
	if isinstance(spell_type, SpellType):
		return spell_type
	return SpellType(str(spell_type))


def _parse_damage_type(damage_type: Any) -> DamageType:
	if isinstance(damage_type, DamageType):
		return damage_type
	if damage_type in (None, ""):
		return DamageType.FORCE
	return DamageType(str(damage_type))


def _get_str(data: dict, key: str) -> str:
	return str(data.get(key, ""))


def _get_int(value: Any) -> int:
	return int(value)


def _get_hit_modifier(data: dict) -> int:
	if "hit_modifier" in data:
		return _get_int(data.get("hit_modifier", 0))
	return _get_int(data.get("hit_modifiers", 0))


def _parse_status_effects(value: Any) -> Optional[List[StatusEffect]]:
	if value is None:
		return None
	if not isinstance(value, list):
		return None

	parsed_effects: List[StatusEffect] = []
	for item in value:
		if isinstance(item, StatusEffect):
			parsed_effects.append(item)
		elif isinstance(item, dict):
			parsed_effects.append(StatusEffect.from_dict(item))
	return parsed_effects


@dataclass
class Spell:
	id: str
	name: str
	description: str
	type: SpellType
	damage_type: DamageType
	value: str
	hit_modifiers: int = 0
	status_effects: Optional[List[StatusEffect]] = None

	def to_dict(self) -> dict:
		return {
			"id": self.id,
			"name": self.name,
			"description": self.description,
			"type": self.type.value,
			"damage_type": self.damage_type.value,
			"value": self.value,
			"hit_modifiers": self.hit_modifiers,
			"status_effects": (
				[status_effect.to_dict() for status_effect in self.status_effects]
				if self.status_effects is not None
				else None
			),
		}

	@classmethod
	def from_dict(cls, data: dict) -> "Spell":
		return cls(
			id=_get_str(data, "id"),
			name=_get_str(data, "name"),
			description=_get_str(data, "description"),
			type=_parse_spell_type(data.get("type")),
			damage_type=_parse_damage_type(data.get("damage_type")),
			value=_get_str(data, "value"),
			hit_modifiers=_get_hit_modifier(data),
			status_effects=_parse_status_effects(data.get("status_effects")),
		)

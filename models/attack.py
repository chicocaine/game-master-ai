from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.enums import AttackType, DamageType
from models.status_effect import StatusEffectInstance


def _parse_attack_type(attack_type: Any) -> AttackType:
	if isinstance(attack_type, AttackType):
		return attack_type
	return AttackType(str(attack_type))


def _parse_damage_type(damage_type: Any) -> DamageType:
	if isinstance(damage_type, DamageType):
		return damage_type
	if damage_type in (None, ""):
		return DamageType.FORCE
	return DamageType(str(damage_type))


def _parse_damage_types(value: Any) -> List[DamageType]:
	if not isinstance(value, list):
		return []

	parsed_damage_types: List[DamageType] = []
	for item in value:
		parsed_damage_types.append(_parse_damage_type(item))
	return parsed_damage_types


def _get_str(data: dict, key: str) -> str:
	return str(data.get(key, ""))


def _get_int(value: Any) -> int:
	return int(value)


def _parse_applied_status_effects(value: Any) -> List[StatusEffectInstance]:
	if not isinstance(value, list):
		return []

	parsed_effects: List[StatusEffectInstance] = []
	for item in value:
		if isinstance(item, StatusEffectInstance):
			parsed_effects.append(item)
		elif isinstance(item, dict):
			parsed_effects.append(StatusEffectInstance.from_dict(item))
	return parsed_effects


def _normalize_parameters(data: dict) -> Dict[str, Any]:
	parameters = data.get("parameters", {})
	if not isinstance(parameters, dict):
		parameters = {}

	damage_types_source = parameters.get("damage_types", [])
	magnitude_source = parameters.get("magnitude", "")
	hit_modifiers_source = parameters.get("hit_modifiers", 0)
	applied_effects_source = parameters.get("applied_status_effects", [])

	return {
		"damage_types": _parse_damage_types(damage_types_source),
		"magnitude": _get_str({"magnitude": magnitude_source}, "magnitude"),
		"hit_modifiers": _get_int(hit_modifiers_source),
		"applied_status_effects": _parse_applied_status_effects(applied_effects_source),
	}


def _serialize_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
	damage_types = _parse_damage_types(parameters.get("damage_types", []))
	magnitude = _get_str({"magnitude": parameters.get("magnitude", "")}, "magnitude")
	hit_modifiers = _get_int(parameters.get("hit_modifiers", 0))
	applied_status_effects = _parse_applied_status_effects(parameters.get("applied_status_effects", []))

	return {
		"damage_types": [damage_type.value for damage_type in damage_types],
		"magnitude": magnitude,
		"hit_modifiers": hit_modifiers,
		"applied_status_effects": [
			status_effect.to_ref() for status_effect in applied_status_effects
		],
	}


@dataclass
class Attack:
	id: str
	name: str
	description: str
	type: AttackType
	parameters: Dict[str, Any] = field(default_factory=dict)

	@property
	def damage_types(self) -> List[DamageType]:
		return _parse_damage_types(self.parameters.get("damage_types", []))

	@property
	def magnitude(self) -> str:
		return _get_str({"magnitude": self.parameters.get("magnitude", "")}, "magnitude")

	@property
	def hit_modifiers(self) -> int:
		return _get_int(self.parameters.get("hit_modifiers", 0))

	@property
	def applied_status_effects(self) -> List[StatusEffectInstance]:
		return _parse_applied_status_effects(self.parameters.get("applied_status_effects", []))

	def to_dict(self) -> dict:
		return {
			"id": self.id,
			"name": self.name,
			"description": self.description,
			"type": self.type.value,
			"parameters": _serialize_parameters(self.parameters),
		}

	@classmethod
	def from_dict(cls, data: dict) -> "Attack":
		return cls(
			id=_get_str(data, "id"),
			name=_get_str(data, "name"),
			description=_get_str(data, "description"),
			type=_parse_attack_type(data.get("type")),
			parameters=_normalize_parameters(data),
		)

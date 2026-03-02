from dataclasses import dataclass, field
from typing import Dict, Any, List

from core.enums import StatusEffectType


def _parse_effect_type(effect_type: Any) -> StatusEffectType:
	if isinstance(effect_type, StatusEffectType):
		return effect_type
	return StatusEffectType(str(effect_type))


def _get_parameters(data: dict) -> Dict[str, Any]:
	params = data.get("parameters", {})
	return dict(params) if isinstance(params, dict) else {}


def _get_str(data: dict, key: str) -> str:
	return str(data.get(key, ""))


@dataclass
class StatusEffectDefinition:
	id: str
	name: str
	description: str
	type: StatusEffectType
	parameters: Dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict:
		return {
			"id": self.id,
			"name": self.name,
			"description": self.description,
			"type": self.type.value,
			"parameters": dict(self.parameters),
		}

	@classmethod
	def from_dict(cls, data: dict) -> "StatusEffectDefinition":
		return cls(
			id=_get_str(data, "id"),
			name=_get_str(data, "name"),
			description=_get_str(data, "description"),
			type=_parse_effect_type(data.get("type")),
			parameters=_get_parameters(data),
		)


def _get_int(value: Any) -> int:
	return int(value)


def _parse_status_effect(value: Any) -> StatusEffectDefinition:
	if isinstance(value, StatusEffectDefinition):
		return value
	if isinstance(value, dict):
		return StatusEffectDefinition.from_dict(value)
	raise ValueError("Invalid status effect payload")


@dataclass
class StatusEffectInstance:
	status_effect: StatusEffectDefinition
	duration: int

	@property
	def id(self) -> str:
		return self.status_effect.id

	def to_ref(self) -> List[Any]:
		return [self.status_effect.id, self.duration]

	@classmethod
	def from_dict(cls, data: dict) -> "StatusEffectInstance":
		status_effect_payload = data.get("status_effect") if "status_effect" in data else data
		return cls(
			status_effect=_parse_status_effect(status_effect_payload),
			duration=_get_int(data.get("duration", 0)),
		)

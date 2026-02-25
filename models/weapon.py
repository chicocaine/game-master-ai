from dataclasses import dataclass, field
from typing import Any, List

from core.enums import WeaponType
from models.attack import Attack


def _parse_weapon_type(weapon_type: Any) -> WeaponType:
	if isinstance(weapon_type, WeaponType):
		return weapon_type
	return WeaponType(str(weapon_type))


def _get_str(data: dict, key: str) -> str:
	return str(data.get(key, ""))


def _parse_known_attacks(value: Any) -> List[Attack]:
	if not isinstance(value, list):
		return []

	attacks: List[Attack] = []
	for item in value:
		if isinstance(item, Attack):
			attacks.append(item)
		elif isinstance(item, dict):
			attacks.append(Attack.from_dict(item))
	return attacks


@dataclass
class Weapon:
	id: str
	name: str
	description: str
	type: WeaponType
	known_attacks: List[Attack] = field(default_factory=list)

	def to_dict(self) -> dict:
		return {
			"id": self.id,
			"name": self.name,
			"description": self.description,
			"type": self.type.value,
			"known_attacks": [attack.to_dict() for attack in self.known_attacks],
		}

	@classmethod
	def from_dict(cls, data: dict) -> "Weapon":
		return cls(
			id=_get_str(data, "id"),
			name=_get_str(data, "name"),
			description=_get_str(data, "description"),
			type=_parse_weapon_type(data.get("type")),
			known_attacks=_parse_known_attacks(data.get("known_attacks", [])),
		)


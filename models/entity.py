from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.enums import DamageType, WeaponType
from models.attack import Attack
from models.archetype import Archetype
from models.race import Race
from models.spell import Spell
from models.weapon import Weapon


def _get_str(data: dict, key: str) -> str:
	return str(data.get(key, ""))


def _get_int(value: Any) -> int:
	return int(value)


def _parse_damage_type(value: Any) -> DamageType:
	if isinstance(value, DamageType):
		return value
	return DamageType(str(value))


def _parse_damage_type_list(value: Any) -> List[DamageType]:
	if not isinstance(value, list):
		return []

	parsed_types: List[DamageType] = []
	for item in value:
		parsed_types.append(_parse_damage_type(item))
	return parsed_types


def _parse_race(value: Any) -> Race:
	if isinstance(value, Race):
		return value
	if isinstance(value, dict):
		return Race.from_dict(value)
	return Race(id="", name="", description="", base_hp=0, base_AC=0)


def _parse_archetype(value: Any) -> Archetype:
	if isinstance(value, Archetype):
		return value
	if isinstance(value, dict):
		return Archetype.from_dict(value)
	return Archetype(id="", name="", description="", hp_mod=0, AC_mod=0)


def _parse_weapon(value: Any) -> Weapon:
	if isinstance(value, Weapon):
		return value
	if isinstance(value, dict):
		return Weapon.from_dict(value)
	return Weapon(id="", name="", description="", type=WeaponType.SIMPLE_MELEE)


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


def _parse_known_spells(value: Any) -> List[Spell]:
	if not isinstance(value, list):
		return []

	spells: List[Spell] = []
	for item in value:
		if isinstance(item, Spell):
			spells.append(item)
		elif isinstance(item, dict):
			spells.append(Spell.from_dict(item))
	return spells


def _dedupe_by_id(items: List[Any]) -> List[Any]:
	seen_ids: Dict[str, bool] = {}
	result: List[Any] = []
	for item in items:
		item_id = getattr(item, "id", None)
		if item_id is None:
			continue
		if item_id in seen_ids:
			continue
		seen_ids[item_id] = True
		result.append(item)
	return result


@dataclass
class Entity:
	id: str
	name: str
	description: str
	race: Race
	archetype: Archetype
	weapon: Weapon
	hp: int
	AC: int
	known_attacks: List[Attack] = field(default_factory=list)
	known_spells: List[Spell] = field(default_factory=list)
	resistances: List[DamageType] = field(default_factory=list)
	immunities: List[DamageType] = field(default_factory=list)
	vulnerabilities: List[DamageType] = field(default_factory=list)

	@property
	def max_hp(self) -> int:
		return self.race.base_hp + self.archetype.hp_mod

	@property
	def base_AC(self) -> int:
		return self.race.base_AC + self.archetype.AC_mod

	@property
	def merged_attacks(self) -> List[Attack]:
		merged = (
			self.race.known_attacks
			+ self.archetype.known_attacks
			+ self.weapon.known_attacks
			+ self.known_attacks
		)
		return _dedupe_by_id(merged)

	@property
	def merged_spells(self) -> List[Spell]:
		merged = self.race.known_spells + self.archetype.known_spells + self.known_spells
		return _dedupe_by_id(merged)

	@property
	def merged_resistances(self) -> List[DamageType]:
		resistances = self.race.resistances + self.archetype.resistances + self.resistances
		return sorted(list(set(resistances)), key=lambda x: x.value)

	@property
	def merged_immunities(self) -> List[DamageType]:
		immunities = self.race.immunities + self.archetype.immunities + self.immunities
		return sorted(list(set(immunities)), key=lambda x: x.value)

	@property
	def merged_vulnerabilities(self) -> List[DamageType]:
		vulnerabilities = self.race.vulnerabilities + self.archetype.vulnerabilities + self.vulnerabilities
		return sorted(list(set(vulnerabilities)), key=lambda x: x.value)

	def to_dict(self) -> dict:
		return {
			"id": self.id,
			"name": self.name,
			"description": self.description,
			"race": self.race.to_dict(),
			"archetype": self.archetype.to_dict(),
			"weapon": self.weapon.to_dict(),
			"hp": self.hp,
			"AC": self.AC,
			"known_attacks": [attack.to_dict() for attack in self.merged_attacks],
			"known_spells": [spell.to_dict() for spell in self.merged_spells],
			"resistances": [damage_type.value for damage_type in self.merged_resistances],
			"immunities": [damage_type.value for damage_type in self.merged_immunities],
			"vulnerabilities": [damage_type.value for damage_type in self.merged_vulnerabilities],
			"max_hp": self.max_hp,
			"base_AC": self.base_AC,
		}

	@classmethod
	def from_dict(cls, data: dict) -> "Entity":
		race_model = _parse_race(data.get("race"))
		archetype_model = _parse_archetype(data.get("archetype", data.get("class")))
		weapon_model = _parse_weapon(data.get("weapon"))

		hp_default = race_model.base_hp + archetype_model.hp_mod
		ac_default = race_model.base_AC + archetype_model.AC_mod

		return cls(
			id=_get_str(data, "id"),
			name=_get_str(data, "name"),
			description=_get_str(data, "description"),
			race=race_model,
			archetype=archetype_model,
			weapon=weapon_model,
			hp=_get_int(data.get("hp", hp_default)),
			AC=_get_int(data.get("AC", ac_default)),
			known_attacks=_parse_known_attacks(data.get("known_attacks", [])),
			known_spells=_parse_known_spells(data.get("known_spells", [])),
			resistances=_parse_damage_type_list(data.get("resistances", [])),
			immunities=_parse_damage_type_list(data.get("immunities", [])),
			vulnerabilities=_parse_damage_type_list(data.get("vulnerabilities", [])),
		)

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.enums import (
    DamageType,
    WeaponProficiency,
    WeaponHandling,
    WeaponWeightClass,
    WeaponDelivery,
    WeaponMagicType,
)
from core.models.attack import Attack
from core.models.archetype import Archetype
from core.models.race import Race
from core.models.spell import Spell
from core.models.status_effect import StatusEffectInstance
from core.models.weapon import Weapon


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
	return Race(id="", name="", description="", base_hp=0, base_AC=0, base_spell_slots=0)


def _parse_archetype(value: Any) -> Archetype:
	if isinstance(value, Archetype):
		return value
	if isinstance(value, dict):
		return Archetype.from_dict(value)
	return Archetype(id="", name="", description="", hp_mod=0, AC_mod=0, spell_slot_mod=0)


def _parse_weapon(value: Any) -> Weapon:
	if isinstance(value, Weapon):
		return value
	if isinstance(value, dict):
		return Weapon.from_dict(value)
	return _default_weapon()


def _default_weapon() -> Weapon:
	return Weapon(
		id="",
		name="",
		description="",
		proficiency=WeaponProficiency.SIMPLE,
		handling=WeaponHandling.ONE_HANDED,
		weight_class=WeaponWeightClass.LIGHT,
		delivery=WeaponDelivery.MELEE,
		magic_type=WeaponMagicType.MUNDANE,
	)


def _parse_weapons(value: Any) -> List[Weapon]:
	if not isinstance(value, list):
		return []

	weapons: List[Weapon] = []
	for item in value:
		if isinstance(item, Weapon):
			weapons.append(item)
		elif isinstance(item, dict):
			weapons.append(Weapon.from_dict(item))
	return weapons


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


def _parse_active_status_effects(value: Any) -> List[StatusEffectInstance]:
	if not isinstance(value, list):
		return []

	effects: List[StatusEffectInstance] = []
	for item in value:
		if isinstance(item, StatusEffectInstance):
			effects.append(item)
		elif isinstance(item, dict):
			effects.append(StatusEffectInstance.from_dict(item))
	return effects


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


def _validate_archetype_constraint(race: Race, archetype: Archetype) -> None:
	allowed_archetypes = getattr(race, "archetype_constraints", [])
	if not allowed_archetypes:
		return
	if archetype.id not in allowed_archetypes:
		raise ValueError(f"Archetype '{archetype.id}' is not allowed for race '{race.id}'")


def _validate_weapon_constraints(archetype: Archetype, weapons: List[Weapon]) -> None:
	constraints = getattr(archetype, "weapon_constraints", None)
	if constraints is None:
		return

	for weapon in weapons:
		if constraints.proficiency and weapon.proficiency not in constraints.proficiency:
			raise ValueError(f"Weapon '{weapon.id}' violates proficiency constraints")
		if constraints.handling and weapon.handling not in constraints.handling:
			raise ValueError(f"Weapon '{weapon.id}' violates handling constraints")
		if constraints.weight_class and weapon.weight_class not in constraints.weight_class:
			raise ValueError(f"Weapon '{weapon.id}' violates weight class constraints")
		if constraints.delivery and weapon.delivery not in constraints.delivery:
			raise ValueError(f"Weapon '{weapon.id}' violates delivery constraints")
		if constraints.magic_type and weapon.magic_type not in constraints.magic_type:
			raise ValueError(f"Weapon '{weapon.id}' violates magic type constraints")


@dataclass
class Entity:
	id: str
	name: str
	description: str
	race: Race
	archetype: Archetype
	hp: int
	max_hp: int
	base_AC: int
	AC: int
	spell_slots: int
	max_spell_slots: int
	active_status_effects: List[StatusEffectInstance] = field(default_factory=list)
	weapons: List[Weapon] = field(default_factory=list)
	known_attacks: List[Attack] = field(default_factory=list)
	known_spells: List[Spell] = field(default_factory=list)
	resistances: List[DamageType] = field(default_factory=list)
	immunities: List[DamageType] = field(default_factory=list)
	vulnerabilities: List[DamageType] = field(default_factory=list)

	@property
	def weapon(self) -> Weapon:
		if self.weapons:
			return self.weapons[0]
		return _default_weapon()

	@property
	def merged_attacks(self) -> List[Attack]:
		weapon_attacks: List[Attack] = []
		for weapon in self.weapons:
			weapon_attacks.extend(weapon.known_attacks)

		merged = (
			self.race.known_attacks
			+ self.archetype.known_attacks
			+ weapon_attacks
			+ self.known_attacks
		)
		return _dedupe_by_id(merged)

	@property
	def merged_spells(self) -> List[Spell]:
		weapon_spells: List[Spell] = []
		for weapon in self.weapons:
			weapon_spells.extend(weapon.known_spells)

		merged = self.race.known_spells + self.archetype.known_spells + weapon_spells + self.known_spells
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
			"weapons": [weapon.to_dict() for weapon in self.weapons],
			"weapon": self.weapon.to_dict(),
			"hp": self.hp,
			"AC": self.AC,
			"spell_slots": self.spell_slots,
			"max_hp": self.max_hp,
			"base_AC": self.base_AC,
			"max_spell_slots": self.max_spell_slots,
			"active_status_effects": [
				status_effect.to_ref() for status_effect in self.active_status_effects
			],
			"known_attacks": [attack.to_dict() for attack in self.merged_attacks],
			"known_spells": [spell.to_dict() for spell in self.merged_spells],
			"resistances": [damage_type.value for damage_type in self.merged_resistances],
			"immunities": [damage_type.value for damage_type in self.merged_immunities],
			"vulnerabilities": [damage_type.value for damage_type in self.merged_vulnerabilities],
		}

	@classmethod
	def create(
		cls,
		id: str,
		name: str,
		description: str,
		race: Any,
		archetype: Any,
		weapons: Any,
		active_status_effects: Any = None,
	) -> "Entity":
		race_model = _parse_race(race)
		archetype_model = _parse_archetype(archetype)
		weapons_model = _parse_weapons(weapons)
		active_status_effects_model = _parse_active_status_effects(active_status_effects)

		_validate_archetype_constraint(race_model, archetype_model)
		_validate_weapon_constraints(archetype_model, weapons_model)

		hp_default = race_model.base_hp + archetype_model.hp_mod
		ac_default = race_model.base_AC + archetype_model.AC_mod
		spell_slots_default = race_model.base_spell_slots + archetype_model.spell_slot_mod
		max_hp_default = hp_default
		max_spell_slots_default = spell_slots_default

		return cls(
			id=id,
			name=name,
			description=description,
			race=race_model,
			archetype=archetype_model,
			weapons=weapons_model,
			hp=hp_default,
			max_hp=max_hp_default,
			AC=ac_default,
			base_AC=ac_default,
			spell_slots=spell_slots_default,
			max_spell_slots=max_spell_slots_default,
			active_status_effects=active_status_effects_model,
		)

	@classmethod
	def from_dict(cls, data: dict) -> "Entity":
		race_model = _parse_race(data.get("race"))
		archetype_model = _parse_archetype(data.get("archetype", data.get("class")))
		weapons_model = _parse_weapons(data.get("weapons", []))
		if not weapons_model:
			legacy_weapon = _parse_weapon(data.get("weapon"))
			if legacy_weapon.id != "":
				weapons_model = [legacy_weapon]

		hp_default = race_model.base_hp + archetype_model.hp_mod
		ac_default = race_model.base_AC + archetype_model.AC_mod
		spell_slots_default = race_model.base_spell_slots + archetype_model.spell_slot_mod
		max_hp_default = hp_default
		max_spell_slots_default = spell_slots_default
		max_spell_slots_value = data.get(
			"max_spell_slots",
			data.get("max_spelll_slots", max_spell_slots_default),
		)

		return cls(
			id=_get_str(data, "id"),
			name=_get_str(data, "name"),
			description=_get_str(data, "description"),
			race=race_model,
			archetype=archetype_model,
			weapons=weapons_model,
			hp=_get_int(data.get("hp", hp_default)),
			max_hp=_get_int(data.get("max_hp", max_hp_default)),
			base_AC=_get_int(data.get("base_AC", ac_default)),
			AC=_get_int(data.get("AC", ac_default)),
			spell_slots=_get_int(data.get("spell_slots", spell_slots_default)),
			max_spell_slots=_get_int(max_spell_slots_value),
			active_status_effects=_parse_active_status_effects(
				data.get("active_status_effects", data.get("status_effects", []))
			),
			known_attacks=_parse_known_attacks(data.get("known_attacks", [])),
			known_spells=_parse_known_spells(data.get("known_spells", [])),
			resistances=_parse_damage_type_list(data.get("resistances", [])),
			immunities=_parse_damage_type_list(data.get("immunities", [])),
			vulnerabilities=_parse_damage_type_list(data.get("vulnerabilities", [])),
		)


def create_entity(
	id: str,
	name: str,
	description: str,
	race: Any,
	archetype: Any,
	weapons: Any,
	active_status_effects: Any = None,
) -> Entity:
	return Entity.create(
		id=id,
		name=name,
		description=description,
		race=race,
		archetype=archetype,
		weapons=weapons,
		active_status_effects=active_status_effects,
	)

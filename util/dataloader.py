import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, TypeVar, Union

from models.archetype import Archetype
from models.attack import Attack
from models.entity import Entity, create_entity
from models.race import Race
from models.spell import Spell
from models.status_effect import StatusEffect
from models.weapon import Weapon


TModel = TypeVar("TModel")


def _load_json(path: Path):
	with path.open("r", encoding="utf-8") as file:
		return json.load(file)


def _index_by_id(items: Iterable[dict], source: str) -> Dict[str, dict]:
	indexed: Dict[str, dict] = {}
	for item in items:
		if not isinstance(item, dict):
			raise ValueError(f"Invalid item in {source}: expected object")
		item_id = str(item.get("id", ""))
		if not item_id:
			raise ValueError(f"Invalid item in {source}: missing 'id'")
		indexed[item_id] = item
	return indexed


def _resolve_ids(
	ids: Optional[List[str]],
	index: Dict[str, TModel],
	ref_name: str,
	owner_id: str,
) -> List[TModel]:
	if not ids:
		return []

	resolved: List[TModel] = []
	for ref_id in ids:
		key = str(ref_id)
		if key not in index:
			raise KeyError(f"Unknown {ref_name} id '{key}' referenced by '{owner_id}'")
		resolved.append(index[key])
	return resolved


@dataclass
class DataCatalog:
	status_effects: Dict[str, StatusEffect]
	attacks: Dict[str, Attack]
	spells: Dict[str, Spell]
	weapons: Dict[str, Weapon]
	races: Dict[str, Race]
	archetypes: Dict[str, Archetype]


def load_catalog(data_dir: Union[str, Path]) -> DataCatalog:
	root = Path(data_dir)

	status_effect_rows = _load_json(root / "status_effects.json")
	attack_rows = _load_json(root / "attacks.json")
	spell_rows = _load_json(root / "spells.json")
	weapon_rows = _load_json(root / "weapons.json")
	race_rows = _load_json(root / "races.json")
	archetype_rows = _load_json(root / "archetypes.json")

	status_effect_data = _index_by_id(status_effect_rows, "status_effects.json")
	attack_data = _index_by_id(attack_rows, "attacks.json")
	spell_data = _index_by_id(spell_rows, "spells.json")
	weapon_data = _index_by_id(weapon_rows, "weapons.json")
	race_data = _index_by_id(race_rows, "races.json")
	archetype_data = _index_by_id(archetype_rows, "archetypes.json")

	status_effects: Dict[str, StatusEffect] = {
		item_id: StatusEffect.from_dict(item)
		for item_id, item in status_effect_data.items()
	}

	attacks: Dict[str, Attack] = {}
	for item_id, raw in attack_data.items():
		resolved_effects = None
		if raw.get("status_effects") is not None:
			resolved_effects = _resolve_ids(
				raw.get("status_effects", []),
				status_effects,
				"status_effect",
				item_id,
			)

		payload = dict(raw)
		payload["status_effects"] = resolved_effects
		attacks[item_id] = Attack.from_dict(payload)

	spells: Dict[str, Spell] = {}
	for item_id, raw in spell_data.items():
		resolved_effects = None
		if raw.get("status_effects") is not None:
			resolved_effects = _resolve_ids(
				raw.get("status_effects", []),
				status_effects,
				"status_effect",
				item_id,
			)

		payload = dict(raw)
		payload["status_effects"] = resolved_effects
		spells[item_id] = Spell.from_dict(payload)

	weapons: Dict[str, Weapon] = {}
	for item_id, raw in weapon_data.items():
		payload = dict(raw)
		payload["known_attacks"] = _resolve_ids(
			raw.get("known_attacks", []), attacks, "attack", item_id
		)
		payload["known_spells"] = _resolve_ids(
			raw.get("known_spells", []), spells, "spell", item_id
		)
		weapons[item_id] = Weapon.from_dict(payload)

	races: Dict[str, Race] = {}
	for item_id, raw in race_data.items():
		payload = dict(raw)
		payload["known_attacks"] = _resolve_ids(
			raw.get("known_attacks", []), attacks, "attack", item_id
		)
		payload["known_spells"] = _resolve_ids(
			raw.get("known_spells", []), spells, "spell", item_id
		)
		races[item_id] = Race.from_dict(payload)

	archetypes: Dict[str, Archetype] = {}
	for item_id, raw in archetype_data.items():
		payload = dict(raw)
		payload["known_attacks"] = _resolve_ids(
			raw.get("known_attacks", []), attacks, "attack", item_id
		)
		payload["known_spells"] = _resolve_ids(
			raw.get("known_spells", []), spells, "spell", item_id
		)
		payload["weapons"] = _resolve_ids(
			raw.get("weapons", []), weapons, "weapon", item_id
		)
		archetypes[item_id] = Archetype.from_dict(payload)

	return DataCatalog(
		status_effects=status_effects,
		attacks=attacks,
		spells=spells,
		weapons=weapons,
		races=races,
		archetypes=archetypes,
	)


def create_entity_from_ids(
	entity_id: str,
	name: str,
	description: str,
	race_id: str,
	archetype_id: str,
	weapon_ids: List[str],
	data_dir: Union[str, Path] = "data",
) -> Entity:
	catalog = load_catalog(data_dir)

	if race_id not in catalog.races:
		raise KeyError(f"Unknown race id '{race_id}'")
	if archetype_id not in catalog.archetypes:
		raise KeyError(f"Unknown archetype id '{archetype_id}'")

	resolved_weapons = _resolve_ids(weapon_ids, catalog.weapons, "weapon", entity_id)

	return create_entity(
		id=entity_id,
		name=name,
		description=description,
		race=catalog.races[race_id],
		archetype=catalog.archetypes[archetype_id],
		weapons=resolved_weapons,
	)

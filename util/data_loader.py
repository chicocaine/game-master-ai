import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, TypeVar, Union

from models.archetype import Archetype
from models.attack import Attack
from models.dungeon import Dungeon
from models.entity import Entity
from models.enemy import Enemy
from models.race import Race
from models.spell import Spell
from models.status_effect import StatusEffectDefinition, StatusEffectInstance
from models.weapon import Weapon
from util.data_validator import validate_dungeon
from util.json_schema_validator import validate_model_data_files


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


def _resolve_status_effect_instances(
	references: Optional[List[list]],
	index: Dict[str, StatusEffectDefinition],
	owner_id: str,
	field_name: str,
) -> List[StatusEffectInstance]:
	if not references:
		return []

	resolved: List[StatusEffectInstance] = []
	for reference in references:
		if not isinstance(reference, list) or len(reference) != 2:
			raise ValueError(
				f"Invalid status effect reference in '{owner_id}.{field_name}': expected [status_effect_id, duration]"
			)

		status_effect_id = str(reference[0])
		duration = int(reference[1])
		if status_effect_id not in index:
			raise KeyError(
				f"Unknown status_effect id '{status_effect_id}' referenced by '{owner_id}'"
			)

		resolved.append(
			StatusEffectInstance(
				status_effect=index[status_effect_id],
				duration=duration,
			)
		)

	return resolved


@dataclass
class DataCatalog:
	status_effects: Dict[str, StatusEffectDefinition]
	attacks: Dict[str, Attack]
	spells: Dict[str, Spell]
	weapons: Dict[str, Weapon]
	races: Dict[str, Race]
	archetypes: Dict[str, Archetype]


def _resolve_entity_payload(raw: dict, catalog: DataCatalog) -> dict:
	entity_id = str(raw.get("id", ""))
	race_id = str(raw.get("race", ""))
	archetype_id = str(raw.get("archetype", raw.get("class", "")))

	if race_id not in catalog.races:
		raise KeyError(f"Unknown race id '{race_id}'")
	if archetype_id not in catalog.archetypes:
		raise KeyError(f"Unknown archetype id '{archetype_id}'")

	payload = dict(raw)
	payload["race"] = catalog.races[race_id]
	payload["archetype"] = catalog.archetypes[archetype_id]
	payload["weapons"] = _resolve_ids(
		raw.get("weapons", []), catalog.weapons, "weapon", entity_id
	)
	payload["known_attacks"] = _resolve_ids(
		raw.get("known_attacks", []), catalog.attacks, "attack", entity_id
	)
	payload["known_spells"] = _resolve_ids(
		raw.get("known_spells", []), catalog.spells, "spell", entity_id
	)
	payload["active_status_effects"] = _resolve_status_effect_instances(
		raw.get("active_status_effects", raw.get("status_effects", [])),
		catalog.status_effects,
		entity_id,
		"active_status_effects",
	)

	return payload


def _load_entity_templates(file_name: str, data_dir: Union[str, Path]) -> Dict[str, Entity]:
	root = Path(data_dir)
	validate_model_data_files(root, [file_name])
	template_rows = _load_json(root / file_name)
	template_data = _index_by_id(template_rows, file_name)
	catalog = load_catalog(root)

	entities: Dict[str, Entity] = {}
	for entity_id, raw in template_data.items():
		payload = _resolve_entity_payload(raw, catalog)
		entities[entity_id] = Entity.from_dict(payload)

	return entities


def load_catalog(data_dir: Union[str, Path]) -> DataCatalog:
	root = Path(data_dir)
	validate_model_data_files(
		root,
		[
			"status_effects.json",
			"attacks.json",
			"spells.json",
			"weapons.json",
			"races.json",
			"archetypes.json",
		],
	)

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

	status_effects: Dict[str, StatusEffectDefinition] = {
		item_id: StatusEffectDefinition.from_dict(item)
		for item_id, item in status_effect_data.items()
	}

	attacks: Dict[str, Attack] = {}
	for item_id, raw in attack_data.items():
		attack_parameters = raw.get("parameters", {})
		if not isinstance(attack_parameters, dict):
			attack_parameters = {}

		resolved_effects = _resolve_status_effect_instances(
			attack_parameters.get("applied_status_effects", []),
			status_effects,
			item_id,
			"applied_status_effects",
		)

		payload = dict(raw)
		payload_parameters = dict(attack_parameters)
		payload_parameters["applied_status_effects"] = resolved_effects
		payload["parameters"] = payload_parameters
		attacks[item_id] = Attack.from_dict(payload)

	spells: Dict[str, Spell] = {}
	for item_id, raw in spell_data.items():
		spell_parameters = raw.get("parameters", {})
		if not isinstance(spell_parameters, dict):
			spell_parameters = {}

		resolved_effects = _resolve_status_effect_instances(
			spell_parameters.get("applied_status_effects", []),
			status_effects,
			item_id,
			"applied_status_effects",
		)

		payload = dict(raw)
		payload_parameters = dict(spell_parameters)
		payload_parameters["applied_status_effects"] = resolved_effects
		payload["parameters"] = payload_parameters
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
def load_player_templates(data_dir: Union[str, Path] = "data") -> Dict[str, Entity]:
	return _load_entity_templates("players.json", data_dir)


def load_enemy_templates(data_dir: Union[str, Path] = "data") -> Dict[str, Entity]:
	return _load_entity_templates("enemies.json", data_dir)


def _load_enemy_template_models(
	data_dir: Union[str, Path],
	catalog: Optional[DataCatalog] = None,
) -> Dict[str, Enemy]:
	root = Path(data_dir)
	validate_model_data_files(root, ["enemies.json"])
	enemy_rows = _load_json(root / "enemies.json")
	enemy_data = _index_by_id(enemy_rows, "enemies.json")
	catalog_data = catalog if catalog is not None else load_catalog(root)

	enemies: Dict[str, Enemy] = {}
	for enemy_id, raw in enemy_data.items():
		payload = _resolve_entity_payload(raw, catalog_data)
		enemies[enemy_id] = Enemy.from_dict(payload)

	return enemies


def load_dungeon_templates(data_dir: Union[str, Path] = "data") -> Dict[str, Dungeon]:
	root = Path(data_dir)
	validate_model_data_files(root, ["dungeons.json"])
	dungeon_rows = _load_json(root / "dungeons.json")
	dungeon_data = _index_by_id(dungeon_rows, "dungeons.json")
	catalog = load_catalog(root)
	enemy_templates = _load_enemy_template_models(root, catalog)

	dungeons: Dict[str, Dungeon] = {}
	for dungeon_id, raw in dungeon_data.items():
		payload = dict(raw)
		room_payloads: List[dict] = []

		for room_raw in raw.get("rooms", []):
			room_payload = dict(room_raw)
			encounter_payloads: List[dict] = []

			for encounter_raw in room_raw.get("encounters", []):
				encounter_payload = dict(encounter_raw)
				encounter_id = str(encounter_raw.get("id", ""))
				encounter_payload["enemies"] = _resolve_ids(
					encounter_raw.get("enemies", []),
					enemy_templates,
					"enemy",
					encounter_id,
				)
				encounter_payloads.append(encounter_payload)

			room_payload["encounters"] = encounter_payloads
			room_payloads.append(room_payload)

		payload["rooms"] = room_payloads
		dungeon = Dungeon.from_dict(payload)
		validate_dungeon(dungeon)
		dungeons[dungeon_id] = dungeon

	return dungeons

from pathlib import Path
from typing import Dict, List, Optional, TypeVar, Union

from core.models.entity import Entity, create_entity
from core.models.enemy import Enemy, create_enemy
from core.models.player import Player, create_player
from core.registry.catalog_registry import DataCatalog, load_catalog_registry


TModel = TypeVar("TModel")


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


def _resolve_catalog_entry(
	catalog: DataCatalog,
	entity_id: str,
	race_id: str,
	archetype_id: str,
	weapon_ids: List[str],
):
	if race_id not in catalog.races:
		raise KeyError(f"Unknown race id '{race_id}'")
	if archetype_id not in catalog.archetypes:
		raise KeyError(f"Unknown archetype id '{archetype_id}'")

	resolved_weapons = _resolve_ids(weapon_ids, catalog.weapons, "weapon", entity_id)
	return catalog.races[race_id], catalog.archetypes[archetype_id], resolved_weapons


def create_entity_from_ids(
	entity_id: str,
	name: str,
	description: str,
	race_id: str,
	archetype_id: str,
	weapon_ids: List[str],
	data_dir: Union[str, Path] = "data",
) -> Entity:
	catalog = load_catalog_registry(data_dir)
	race, archetype, weapons = _resolve_catalog_entry(
		catalog, entity_id, race_id, archetype_id, weapon_ids
	)

	return create_entity(
		id=entity_id,
		name=name,
		description=description,
		race=race,
		archetype=archetype,
		weapons=weapons,
	)


def create_player_from_ids(
	entity_id: str,
	name: str,
	description: str,
	race_id: str,
	archetype_id: str,
	weapon_ids: List[str],
	player_instance_id: str,
	data_dir: Union[str, Path] = "data",
) -> Player:
	catalog = load_catalog_registry(data_dir)
	race, archetype, weapons = _resolve_catalog_entry(
		catalog, entity_id, race_id, archetype_id, weapon_ids
	)

	return create_player(
		id=entity_id,
		name=name,
		description=description,
		race=race,
		archetype=archetype,
		weapons=weapons,
		player_instance_id=player_instance_id,
	)


def create_enemy_from_ids(
	entity_id: str,
	name: str,
	description: str,
	race_id: str,
	archetype_id: str,
	weapon_ids: List[str],
	enemy_instance_id: str,
	data_dir: Union[str, Path] = "data",
) -> Enemy:
	catalog = load_catalog_registry(data_dir)
	race, archetype, weapons = _resolve_catalog_entry(
		catalog, entity_id, race_id, archetype_id, weapon_ids
	)

	return create_enemy(
		id=entity_id,
		name=name,
		description=description,
		race=race,
		archetype=archetype,
		weapons=weapons,
		enemy_instance_id=enemy_instance_id,
	)

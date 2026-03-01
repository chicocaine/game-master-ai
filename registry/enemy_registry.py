from pathlib import Path
from typing import Dict, Optional, Union

from models.enemy import Enemy
from models.entity import Entity
from registry.common import load_indexed_rows
from registry.entity_registry import load_entity_registry, resolve_entity_payload


from registry.catalog_registry import DataCatalog


def load_enemy_registry(
	data_dir: Union[str, Path] = "data",
	catalog: Optional["DataCatalog"] = None,
) -> Dict[str, Entity]:
	return load_entity_registry("enemies.json", data_dir=data_dir, catalog=catalog)


def load_enemy_model_registry(
	data_dir: Union[str, Path] = "data",
	catalog: Optional["DataCatalog"] = None,
) -> Dict[str, Enemy]:
	from registry.catalog_registry import load_catalog_registry

	enemy_data = load_indexed_rows(data_dir, "enemies.json")
	catalog_data = catalog if catalog is not None else load_catalog_registry(data_dir)

	enemies: Dict[str, Enemy] = {}
	for enemy_id, raw in enemy_data.items():
		payload = resolve_entity_payload(raw, catalog_data)
		enemies[enemy_id] = Enemy.from_dict(payload)

	return enemies

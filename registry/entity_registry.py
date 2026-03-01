from pathlib import Path
from typing import Dict, Optional, Union

from models.entity import Entity
from registry.common import resolve_ids, resolve_status_effect_instances


from registry.catalog_registry import DataCatalog


def resolve_entity_payload(raw: dict, catalog: "DataCatalog") -> dict:
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
	payload["weapons"] = resolve_ids(
		raw.get("weapons", []), catalog.weapons, "weapon", entity_id
	)
	payload["known_attacks"] = resolve_ids(
		raw.get("known_attacks", []), catalog.attacks, "attack", entity_id
	)
	payload["known_spells"] = resolve_ids(
		raw.get("known_spells", []), catalog.spells, "spell", entity_id
	)
	payload["active_status_effects"] = resolve_status_effect_instances(
		raw.get("active_status_effects", raw.get("status_effects", [])),
		catalog.status_effects,
		entity_id,
		"active_status_effects",
	)

	return payload


def load_entity_registry(
	file_name: str,
	data_dir: Union[str, Path] = "data",
	catalog: Optional["DataCatalog"] = None,
) -> Dict[str, Entity]:
	from registry.catalog_registry import load_catalog_registry
	from registry.common import load_indexed_rows

	template_data = load_indexed_rows(data_dir, file_name)
	catalog_data = catalog if catalog is not None else load_catalog_registry(data_dir)

	entities: Dict[str, Entity] = {}
	for entity_id, raw in template_data.items():
		payload = resolve_entity_payload(raw, catalog_data)
		entities[entity_id] = Entity.from_dict(payload)

	return entities

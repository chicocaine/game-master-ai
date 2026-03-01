from pathlib import Path
from typing import Dict, List, Optional, Union

from models.dungeon import Dungeon
from models.enemy import Enemy
from registry.common import index_by_id, load_json, resolve_ids, validate_files
from registry.enemy_registry import load_enemy_model_registry
from util.data_validator import validate_dungeon

if False:
	from registry.catalog_registry import DataCatalog


def load_dungeon_registry(
	data_dir: Union[str, Path] = "data",
	catalog: Optional["DataCatalog"] = None,
	enemy_templates: Optional[Dict[str, Enemy]] = None,
) -> Dict[str, Dungeon]:
	root = validate_files(data_dir, ["dungeons.json"])
	rows = load_json(root / "dungeons.json")
	dungeon_data = index_by_id(rows, "dungeons.json")

	if enemy_templates is not None:
		enemy_index = enemy_templates
	else:
		enemy_index = load_enemy_model_registry(root, catalog=catalog)

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
				encounter_payload["enemies"] = resolve_ids(
					encounter_raw.get("enemies", []),
					enemy_index,
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

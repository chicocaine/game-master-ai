from pathlib import Path
from typing import Dict, Union

from models.status_effect import StatusEffectDefinition
from registry.common import index_by_id, load_json, validate_files


def load_status_effect_registry(
	data_dir: Union[str, Path] = "data",
) -> Dict[str, StatusEffectDefinition]:
	root = validate_files(data_dir, ["status_effects.json"])
	rows = load_json(root / "status_effects.json")
	status_effect_data = index_by_id(rows, "status_effects.json")

	return {
		item_id: StatusEffectDefinition.from_dict(item)
		for item_id, item in status_effect_data.items()
	}

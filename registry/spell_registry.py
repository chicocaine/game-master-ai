from pathlib import Path
from typing import Dict, Optional, Union

from models.spell import Spell
from models.status_effect import StatusEffectDefinition
from registry.common import (
	index_by_id,
	load_json,
	resolve_status_effect_instances,
	validate_files,
)
from registry.status_effect_registry import load_status_effect_registry


def load_spell_registry(
	data_dir: Union[str, Path] = "data",
	status_effects: Optional[Dict[str, StatusEffectDefinition]] = None,
) -> Dict[str, Spell]:
	root = validate_files(data_dir, ["spells.json"])
	rows = load_json(root / "spells.json")
	spell_data = index_by_id(rows, "spells.json")
	status_effect_index = (
		status_effects if status_effects is not None else load_status_effect_registry(root)
	)

	spells: Dict[str, Spell] = {}
	for item_id, raw in spell_data.items():
		spell_parameters = raw.get("parameters", {})
		if not isinstance(spell_parameters, dict):
			spell_parameters = {}

		resolved_effects = resolve_status_effect_instances(
			spell_parameters.get("applied_status_effects", []),
			status_effect_index,
			item_id,
			"applied_status_effects",
		)

		payload = dict(raw)
		payload_parameters = dict(spell_parameters)
		payload_parameters["applied_status_effects"] = resolved_effects
		payload["parameters"] = payload_parameters
		spells[item_id] = Spell.from_dict(payload)

	return spells

from pathlib import Path
from typing import Dict, Optional, Union

from core.models.attack import Attack
from core.models.status_effect import StatusEffectDefinition
from core.registry.common import (
	index_by_id,
	load_json,
	resolve_status_effect_instances,
	validate_files,
)
from core.registry.status_effect_registry import load_status_effect_registry


def load_attack_registry(
	data_dir: Union[str, Path] = "data",
	status_effects: Optional[Dict[str, StatusEffectDefinition]] = None,
) -> Dict[str, Attack]:
	root = validate_files(data_dir, ["attacks.json"])
	rows = load_json(root / "attacks.json")
	attack_data = index_by_id(rows, "attacks.json")
	status_effect_index = (
		status_effects if status_effects is not None else load_status_effect_registry(root)
	)

	attacks: Dict[str, Attack] = {}
	for item_id, raw in attack_data.items():
		attack_parameters = raw.get("parameters", {})
		if not isinstance(attack_parameters, dict):
			attack_parameters = {}

		resolved_effects = resolve_status_effect_instances(
			attack_parameters.get("applied_status_effects", []),
			status_effect_index,
			item_id,
			"applied_status_effects",
		)

		payload = dict(raw)
		payload_parameters = dict(attack_parameters)
		payload_parameters["applied_status_effects"] = resolved_effects
		payload["parameters"] = payload_parameters
		attacks[item_id] = Attack.from_dict(payload)

	return attacks

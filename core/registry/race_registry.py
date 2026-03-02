from pathlib import Path
from typing import Dict, Optional, Union

from core.models.attack import Attack
from core.models.race import Race
from core.models.spell import Spell
from core.registry.attack_registry import load_attack_registry
from core.registry.common import index_by_id, load_json, resolve_ids, validate_files
from core.registry.spell_registry import load_spell_registry


def load_race_registry(
	data_dir: Union[str, Path] = "data",
	attacks: Optional[Dict[str, Attack]] = None,
	spells: Optional[Dict[str, Spell]] = None,
) -> Dict[str, Race]:
	root = validate_files(data_dir, ["races.json"])
	rows = load_json(root / "races.json")
	race_data = index_by_id(rows, "races.json")
	attack_index = attacks if attacks is not None else load_attack_registry(root)
	spell_index = spells if spells is not None else load_spell_registry(root)

	items: Dict[str, Race] = {}
	for item_id, raw in race_data.items():
		payload = dict(raw)
		payload["known_attacks"] = resolve_ids(
			raw.get("known_attacks", []), attack_index, "attack", item_id
		)
		payload["known_spells"] = resolve_ids(
			raw.get("known_spells", []), spell_index, "spell", item_id
		)
		items[item_id] = Race.from_dict(payload)

	return items

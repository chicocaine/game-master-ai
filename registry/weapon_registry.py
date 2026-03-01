from pathlib import Path
from typing import Dict, Optional, Union

from models.attack import Attack
from models.spell import Spell
from models.weapon import Weapon
from registry.attack_registry import load_attack_registry
from registry.common import index_by_id, load_json, resolve_ids, validate_files
from registry.spell_registry import load_spell_registry


def load_weapon_registry(
	data_dir: Union[str, Path] = "data",
	attacks: Optional[Dict[str, Attack]] = None,
	spells: Optional[Dict[str, Spell]] = None,
) -> Dict[str, Weapon]:
	root = validate_files(data_dir, ["weapons.json"])
	rows = load_json(root / "weapons.json")
	weapon_data = index_by_id(rows, "weapons.json")
	attack_index = attacks if attacks is not None else load_attack_registry(root)
	spell_index = spells if spells is not None else load_spell_registry(root)

	weapons: Dict[str, Weapon] = {}
	for item_id, raw in weapon_data.items():
		payload = dict(raw)
		payload["known_attacks"] = resolve_ids(
			raw.get("known_attacks", []), attack_index, "attack", item_id
		)
		payload["known_spells"] = resolve_ids(
			raw.get("known_spells", []), spell_index, "spell", item_id
		)
		weapons[item_id] = Weapon.from_dict(payload)

	return weapons

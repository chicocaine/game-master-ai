from pathlib import Path
from typing import Dict, Optional, Union

from models.archetype import Archetype
from models.attack import Attack
from models.spell import Spell
from models.weapon import Weapon
from registry.attack_registry import load_attack_registry
from registry.common import index_by_id, load_json, resolve_ids, validate_files
from registry.spell_registry import load_spell_registry
from registry.weapon_registry import load_weapon_registry


def load_archetype_registry(
	data_dir: Union[str, Path] = "data",
	attacks: Optional[Dict[str, Attack]] = None,
	spells: Optional[Dict[str, Spell]] = None,
	weapons: Optional[Dict[str, Weapon]] = None,
) -> Dict[str, Archetype]:
	root = validate_files(data_dir, ["archetypes.json"])
	rows = load_json(root / "archetypes.json")
	archetype_data = index_by_id(rows, "archetypes.json")
	attack_index = attacks if attacks is not None else load_attack_registry(root)
	spell_index = spells if spells is not None else load_spell_registry(root)
	weapon_index = (
		weapons
		if weapons is not None
		else load_weapon_registry(root, attacks=attack_index, spells=spell_index)
	)

	archetypes: Dict[str, Archetype] = {}
	for item_id, raw in archetype_data.items():
		payload = dict(raw)
		payload["known_attacks"] = resolve_ids(
			raw.get("known_attacks", []), attack_index, "attack", item_id
		)
		payload["known_spells"] = resolve_ids(
			raw.get("known_spells", []), spell_index, "spell", item_id
		)
		payload["weapons"] = resolve_ids(raw.get("weapons", []), weapon_index, "weapon", item_id)
		archetypes[item_id] = Archetype.from_dict(payload)

	return archetypes

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Union

from core.models.archetype import Archetype
from core.models.attack import Attack
from core.models.race import Race
from core.models.spell import Spell
from core.models.status_effect import StatusEffectDefinition
from core.models.weapon import Weapon
from core.registry.archetype_registry import load_archetype_registry
from core.registry.attack_registry import load_attack_registry
from core.registry.race_registry import load_race_registry
from core.registry.spell_registry import load_spell_registry
from core.registry.status_effect_registry import load_status_effect_registry
from core.registry.weapon_registry import load_weapon_registry
from util.json_schema_validator import validate_model_data_files


@dataclass
class DataCatalog:
	status_effects: Dict[str, StatusEffectDefinition]
	attacks: Dict[str, Attack]
	spells: Dict[str, Spell]
	weapons: Dict[str, Weapon]
	races: Dict[str, Race]
	archetypes: Dict[str, Archetype]


def load_catalog_registry(data_dir: Union[str, Path] = "data") -> DataCatalog:
	root = Path(data_dir)
	validate_model_data_files(
		root,
		[
			"status_effects.json",
			"attacks.json",
			"spells.json",
			"weapons.json",
			"races.json",
			"archetypes.json",
		],
	)

	status_effects = load_status_effect_registry(root)
	attacks = load_attack_registry(root, status_effects=status_effects)
	spells = load_spell_registry(root, status_effects=status_effects)
	weapons = load_weapon_registry(root, attacks=attacks, spells=spells)
	races = load_race_registry(root, attacks=attacks, spells=spells)
	archetypes = load_archetype_registry(
		root,
		attacks=attacks,
		spells=spells,
		weapons=weapons,
	)

	return DataCatalog(
		status_effects=status_effects,
		attacks=attacks,
		spells=spells,
		weapons=weapons,
		races=races,
		archetypes=archetypes,
	)

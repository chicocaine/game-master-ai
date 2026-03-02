from core.registry.archetype_registry import load_archetype_registry
from core.registry.attack_registry import load_attack_registry
from core.registry.catalog_registry import DataCatalog, load_catalog_registry
from core.registry.dungeon_registry import load_dungeon_registry
from core.registry.enemy_registry import load_enemy_model_registry, load_enemy_registry
from core.registry.entity_registry import load_entity_registry
from core.registry.player_registry import load_player_registry
from core.registry.race_registry import load_race_registry
from core.registry.spell_registry import load_spell_registry
from core.registry.status_effect_registry import load_status_effect_registry
from core.registry.weapon_registry import load_weapon_registry

__all__ = [
    "DataCatalog",
    "load_catalog_registry",
    "load_status_effect_registry",
    "load_attack_registry",
    "load_spell_registry",
    "load_weapon_registry",
    "load_race_registry",
    "load_archetype_registry",
    "load_entity_registry",
    "load_player_registry",
    "load_enemy_registry",
    "load_enemy_model_registry",
    "load_dungeon_registry",
]

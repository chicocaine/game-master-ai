# Data Schemata
> data schemata for game data JSON storage 

## Runtime Schema Validation
- JSON data files are validated against JSON schemata before model parsing/resolution.
- Validator module: `util/json_schema_validator.py`
- Entrypoint: `validate_model_data_files(data_dir, file_names)`
- Mapping covers all model data files:
	- `status_effects.json -> status_effect.schema.json`
	- `attacks.json -> attack.schema.json`
	- `spells.json -> spell.schema.json`
	- `weapons.json -> weapon.schema.json`
	- `races.json -> race.schema.json`
	- `archetypes.json -> archetype.schema.json`
	- `players.json -> entity.schema.json`
	- `enemies.json -> entity.schema.json`
	- `dungeons.json -> dungeon.schema.json`

## StatusEffect
- Schema file: `data/schemata/status_effect.schema.json`
- Describes serialized status effect objects from `models/status_effect.py`
- Includes a root schema for a single status effect
- Includes `$defs.statusEffectCollection` for arrays

## Attack
- Schema file: `data/schemata/attack.schema.json`
- Describes serialized attack objects from `models/attack.py`
- Includes top-level `damage_type`
- Supports nullable `status_effects` or an array of `status_effect` IDs

## Spell
- Schema file: `data/schemata/spell.schema.json`
- Describes serialized spell objects from `models/spell.py`
- Includes top-level `damage_type`
- Supports nullable `status_effects` or an array of `status_effect` IDs

## Race
- Schema file: `data/schemata/race.schema.json`
- Describes serialized race objects from `models/race.py`
- Includes base stats, resistances/immunities/vulnerabilities, `archetype_constraints`, and ID references for known attacks/spells

## Archetype
- Schema file: `data/schemata/archetype.schema.json`
- Describes serialized archetype objects from `models/archetype.py`
- Includes stat modifiers, resistances/immunities/vulnerabilities, `weapon_constraints`, and ID references for known attacks/spells/weapons

## Weapon
- Schema file: `data/schemata/weapon.schema.json`
- Describes serialized weapon objects from `models/weapon.py`
- Includes `proficiency`, `handling`, `weight_class`, `delivery`, and `magic_type`
- Uses ID references for `known_attacks` and `known_spells`

## Entity Storage Collections
- Schema file: `data/schemata/entity.schema.json`
- `data/players.json` and `data/enemies.json` both store entity-shaped records
- Storage remains schema-compatible `Entity` data (no runtime instance IDs)
- Runtime conversion to `Player` / `Enemy` occurs when records are loaded into game state

Resolver entrypoints for ID-based storage:
- `util/data_loader.py -> load_player_templates(...)`
- `util/data_loader.py -> load_enemy_templates(...)`
- `util/entity_factory.py -> create_entity_from_ids(...)`
- `util/entity_factory.py -> create_player_from_ids(...)`
- `util/entity_factory.py -> create_enemy_from_ids(...)`

## Dungeon
- Schema file: `data/schemata/dungeon.schema.json`
- Describes serialized dungeon objects from `models/dungeon.py`
- Includes nested `room` and `encounter` definitions
- Uses enemy ID references inside each encounter `enemies` array

Resolver entrypoint for dungeon storage:
- `util/data_loader.py -> load_dungeon_templates(...)`

Dungeon integrity validation (separate from data loading):
- `util/data_validator.py -> validate_dungeon(...)`
- Enforces room graph integrity (`start_room`, `end_room`, room connections, and end-room reachability)

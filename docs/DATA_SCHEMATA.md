# Data Schemata
> data schemata for game data JSON storage 

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

Resolver entrypoint for ID-based storage: `util/dataloader.py -> create_entity_from_ids(...)`

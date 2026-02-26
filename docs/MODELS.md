# Models
> Model documentation with type definitions

## Damage Types

<!-- Status Effect Model -->
## Status Effect
> Affects entity stats
### Attributes
- `id`
- `name`
- `description`
- `type`
- `parameters` - based on status effect type

<!-- Attack Model -->
## Attack
> Defines attack action attributes and effects
- `id`
- `name`
- `description`
- `type`
- `damage_type`
- `value`
- `hit_modifiers`
- `status_effects` - ARRAY, NULLABLE

<!-- Spell Model -->
## Spell
> Defines cast spell action attributes and effects
- `id`
- `name`
- `description`
- `type`
- `damage_type`
- `value`
- `hit_modifiers`
- `status_effects` - ARRAY, NULLABLE


<!-- Race Model -->
## Race
> Defines base stats, immunities, resistances, and weaknesses
### Attributes:
- `id` (str)
- `name` (str)
- `description` (str)
- `base_hp` (int)
- `base_AC` (int)
- `resistances` (array of damage types)
- `immunities` (array of damage types)
- `vulnerabilities` (array of damage types)
- `archetype_constraints` (array of archetypes allowed to be paired with this race)
- `known_spells` (array of spell IDs)
- `known_attacks` (array of attack IDs)

<!-- Weapon Model -->
## Weapon
> Defines weapon attributes and stat modifiers
- `id` (str)
- `name` (str)
- `description` (str)
- `proficiency` (weapon proficiency)
- `handling` (weapon handling)
- `weight_class` (weapon weight class)
- `delivery` (weapon delivery)
- `magic_type` (weapon magic type)
- `known_attacks` (array of attack IDs)
- `known_spells` (array of spell IDs)

<!-- Archetype Model -->
## Archetype
> Defines stat modifiers, immunities, resistances, weaknesses, and weapon type  
- `id` (str)
- `name` (str)
- `description`(str)
- `hp_mod` (int)
- `AC_mod` (int)
- `resistances` (array of damage types)
- `immunities` (array of damage types)
- `vulnerabilities` (array of damage types)
- `weapon_constraints` { proficiency: [], handling: [], weight_class: [], delivery: [], magic_type: [] } (allowed weapon attributes for the archetype)
- `known_spells` (array of spell IDs)
- `known_attacks` (array of attack IDs)

<!-- Entity Model -->
## Entity
> Defines and encapsulates all defined race, archetype and weapon attributes
- `id` (str)
- `name` (str)
- `description` (str)
- `race` (race model)
- `archetype` (archetype model)
- `weapons` (array of weapon models)
- `hp` (int)
- `AC` (int)
- `known attacks`
- `known spells`    
- `resistances` (array of damage types)
- `immunities` (array of damage types)
- `vulnerabilities` (array of damage types)

<!-- TODO: -->
<!-- Dungeon Model -->



<!-- Event Model -->
## Event
> Defined events
- `id`
- `type`
- `description`
- `parameters`

<!-- Action Model -->
## Action
> Changes/Can affect the game state
- `id`
- `type`
- `description`
- `parameters`

<!-- Narration Model -->
## Narration
> LLM narration based on context and event
- `id`
- `event_id`
- `text`
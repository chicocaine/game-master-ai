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
- `known_spells` (array of spell model)
- `known_attacks` (array of attack model)

<!-- Weapon Model -->
## Weapon
> Defines weapon attributes and stat modifiers
- `id` (str)
- `name` (str)
- `description` (str)
- `type` (weapon type `core/types.py`)
- `known_attacks` (array of attack model)

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
- `known_spells` (array of spell model)
- `known_attacks` (array of attack model)
- `weapons` (array of weapon model)

<!-- Entity Model -->
## Entity
> Defines and encapsulates all defined race, archetype and weapon attributes
- `id` (str)
- `name` (str)
- `description` (str)
- `race` (race model)
- `archetype` (archetype model)
- `weapon` (weapon model)
- `hp` (int)
- `AC` (int)
- `known attacks`
- `known spells`    
- `resistances` (array of damage types)
- `immunities` (array of damage types)
- `vulnerabilities` (array of damage types)

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
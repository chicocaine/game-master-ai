# Models
> Model documentation with type definitions

## Damage Types

<!-- Status Effect Model -->
## Status Effect
> Affects entity stats
### StatusEffectDefinition Attributes
- `id`
- `name`
- `description`
- `type`
- `parameters` - based on status effect type

### StatusEffectInstance Attributes
- `status_effect` (`StatusEffectDefinition`)
- `duration` (int)
- serialized ref format: `[status_effect_id (str), duration (int)]`

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
- `applied_status_effects` - ARRAY (non-optional), each item is `[status_effect_id, duration]`

<!-- Spell Model -->
## Spell
> Defines cast spell action attributes and effects
- `id`
- `name`
- `description`
- `type`
- `damage_type`
- `spell_cost`
- `value`
- `hit_modifiers`
- `applied_status_effects` - ARRAY (non-optional), each item is `[status_effect_id, duration]`


<!-- Race Model -->
## Race
> Defines base stats, immunities, resistances, and weaknesses
### Attributes:
- `id` (str)
- `name` (str)
- `description` (str)
- `base_hp` (int)
- `base_AC` (int)
- `base_spell_slots` (int) 
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
- `spell_slot_mod` (int) 
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
- `spell_slots` (int)
- `max_hp` (int)
- `max_spell_slots` (int)
- `active_status_effects` (array of `[status_effect_id, duration]`)
- `known_attacks`
- `known_spells`    
- `resistances` (array of damage types)
- `immunities` (array of damage types)
- `vulnerabilities` (array of damage types)

## Player
> Entity specialization for player-controlled instances
- all `Entity` attributes
- `player_instance_id` (str)

## Enemy
> Entity specialization for enemy-controlled instances
- all `Entity` attributes
- `enemy_instance_id` (str)

<!-- TODO: -->
## Dungeon
> Node-based game environment made up of connected rooms

### Encounter
- `id` (str)
- `name` (str)
- `description` (str)
- `difficulty` (difficulty type)
- `cleared` (bool)
- `clear_reward` (int)
- `enemies` (array of enemy models; stored as enemy IDs in JSON)

### Room
- `id` (str)
- `name` (str)
- `description` (str)
- `is_visited` (bool)
- `is_cleared` (bool)
- `is_rested` (bool)
- `connections` (array of room IDs)
- `encounters` (array of encounter models)
- `allowed_rests` (array of rest types)

### Dungeon
- `id` (str)
- `name` (str)
- `description` (str)
- `difficulty` (difficulty type)
- `start_room` (room ID)
- `end_room` (room ID)
- `rooms` (array of room models)



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
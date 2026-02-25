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
- `parameters`

<!-- Spell Model -->
## Spell
> Defines cast spell action attributes and effects
- `id`
- `name`
- `description`
- `type`
- `parameters`


<!-- Race Model -->
## Race
> Defines base stats, proficiencies, immunities, resistances, and weaknesses
### Attributes:
- `id`
- `name`
- `description`
- `hp`
- `AC`
- `proficiencies`
- `resistances`
- `immunities`
- `vulnerabilities`
- `known_spells`
- `known_attacks`

<!-- Weapon Model -->
## Weapon
> Defines weapon attributes and stat modifiers
- `id`
- `name`
- `description`
- `type`
- `parameters`

<!-- Class Model -->
## Class
> Defines stat modifiers, proficiencies, immunities, resistances, weaknesses, and weapon type  
- `id`
- `name`
- `description`
- `modifiers`
- `proficiencies`
- `resistances`
- `immunities`
- `vulnerabilities`
- `weapon_id`

<!-- Entity Model -->
## Entity
> Defines and encapsulates all defined race, class and weapon attributes
- `id`
- `name`
- `description`
- `race_id`
- `class_id`
- `weapon_id`
- `hp`
- `AC`
- `known attacks`
- `known spells`    
- `proficiencies`
- `resistances`
- `immunities`
- `vulnerabilities`

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
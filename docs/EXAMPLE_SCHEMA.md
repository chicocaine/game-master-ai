## Example Node Based Dungeon
```json
{
  "dungeon_id": "crypt_of_whispers",
  "start_room": "room_1",
  "exit_room": "room_treasure",
  "rooms": {
    "room_1": {
      "name": "Entrance",
      "description": "A dimly lit stone entrance.",
      "connections": ["room_2"],
      "encounter": false,
      "rest_allowed": false
    },
    "room_2": {
      "name": "Hallway",
      "description": "A narrow hallway with mossy walls.",
      "connections": ["room_1", "room_3"],
      "encounter": true,
      "encounter_id": "goblin_patrol",
      "rest_allowed": false
    },
    "room_3": {
      "name": "Safe Room",
      "description": "A quiet chamber. You feel safe here.",
      "connections": ["room_2"],
      "encounter": false,
      "rest_allowed": true
    },
    "room_treasure": {
      "name": "Treasure Chamber",
      "description": "Gold and gems glimmer in the torchlight. This is the exit.",
      "connections": ["room_3"],
      "encounter": false,
      "is_exit": true,
      "rest_allowed": false
    }
  }
}
```
## Entities (player, enemies)
```json
{
  "id": "entity_001",
  "name": "Arin",
  "type": "player",
  "race": "human",
  "class": "wizard",

  "hp": 8,
  "max_hp": 8,
  "ac": 11,

  "attack_modifier": 2,

  "known_attacks": ["staff_strike"],
  "spell_slots": {
    "current": 3,
    "max": 3
  },
  "known_spells": ["fire_bolt", "poison_cloud"],

  "status_effects": []
}

```

## Race Schema
> Races are mostly flavor, with optional light modifiers.
```json
{
  "id": "human",
  "description": "Adaptable and resilient.",
  "modifiers": {
    "max_hp": 0,
    "attack_modifier": 0
  }
}

```

## Class Schema
> Classes define starting loadouts, not behavior.
```json
{
  "id": "wizard",
  "starting_hp": 8,
  "base_ac": 11,
  "attack_modifier": 2,
  "starting_spell_slots": 3,
  "allowed_attacks": ["staff_strike"],
  "starting_spells": ["fire_bolt", "heal"]
}

```

## Attack Schema
```json
{
  "id": "staff_strike",
  "name": "Staff Strike",
  "type": "melee | ranged | magical",
  "target": "enemy | ally | self | enemies | allies",
  "to_hit_modifier": 0,
  "damage": "1d6",
  "status_effect": null
}
{
  "id": "poison_dagger",
  "name": "Poison Dagger",
  "type": "melee",
  "to_hit_modifier": 1,
  "damage": "1d4",
  "status_effect": {
    "type": "poisoned",
    "duration": 3,
    "magnitude": 1
  }
}
```

## Spell Schema
```json
{
  "id": "fire_blast",
  "name": "Fire Blast",
  "category": "damage | heal | status | cleanse | aoe | utility",
  "target": "enemy | ally | self | enemies | allies",

  "damage": "1d6",
  "heal": null,

  "status_effect": {
    "type": "burning",
    "duration": 2,
    "magnitude": 2
  },

  "cleanses": null,
  "cost": 1
}
{
  "id": "purify",
  "name": "Purify",
  "category": "cleanse",
  "target": "ally",
  "cleanses": ["poisoned", "burning"],
  "cost": 1
}

```
> AoE works like `"target": "enemies"`

## Status Effect Schema
```json
{
  "type": "poisoned | stunned | burning | weakened | strengthened | fortified | vulnerable",
  "duration": 2,
  "magnitude": 2
}

```

## Encounter Schema
```json
{
  "id": "goblin_casters",
  "enemies": ["goblin_shaman", "goblin_fighter"],
  "reward": 50
}
```

**Fields:**

* **id**: Unique identifier for this encounter
* **enemies**: Array of enemy template IDs to spawn
* **reward**: Points/coins awarded to party upon victory  
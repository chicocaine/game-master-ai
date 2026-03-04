# Actions
> Parsed actions that are sent out by the LLM based on player input. This will be sent through the game engine and will be resolved deterministically

## Base Definition

All parsed actions should be normalized into one base shape before resolution.

```json
{
	"type": "<ActionType>",
	"actor_instance_id": "<string>",
	"parameters": {},
	"raw_input": "<string>",
	"reasoning": "<string>",
	"metadata": {
		"source": "llm",
		"request_id": "<string>",
		"timestamp": "<iso-8601>"
	}
}
```

### Base Fields

1. `type` (required): one of `ActionType` values.
2. `actor_instance_id` (optional): who initiated the action. Not required for lobby/system actions.
3. `parameters` (required): action-specific arguments.
4. `raw_input` (optional): original user utterance.
5. `reasoning` (optional): short machine-readable intent summary.
6. `metadata` (optional): tracing/debug payload.

## Canonical Terms

- Use `target_instance_ids` for attack/spell targets (string or string[]).
- Use `race`, `archetype`, and `weapons` in `create_player` parameters.
- Use `spell_slots` as the canonical spell resource field.
- `MANA_UPDATED` / `mana_updated` remains a legacy event name; resource values are carried in `spell_slots` (and may include `mana` as compatibility alias).

## Parameters by Action Type

### Global

#### `abandon`
- Purpose: abort current run/session.
- Parameters: `{}` (none)

#### `query`
- Purpose: ask for information without mutating game state.
- Parameters:
	- `question` (required, string)
	- `scope` (optional, string; examples: `rules`, `state`, `dungeon`, `party`)

#### `converse`
- Purpose: in-world dialogue action that can influence narration, quests, and NPC state.
- Parameters:
	- `message` (required, string)
	- `target_instance_id` (optional, string; NPC/entity being addressed)
	- `tone` (optional, string; examples: `friendly`, `neutral`, `hostile`, `deceptive`)
	- `intent` (optional, string; examples: `ask`, `persuade`, `threaten`, `barter`)

### Exploration

#### `move`
- Purpose: move actor/party to an adjacent room.
- Parameters:
	- `destination_room_id` (required, string)
	- `path` (optional, string[])

#### `explore`
- Purpose: inspect current room or target in room.
- Parameters:
	- `target` (optional, string; examples: `room`, `object`, `encounter`, `loot`)

#### `rest`
- Purpose: execute a rest action in a room that allows rest.
- Parameters:
	- `rest_type` (required, enum `RestType`: `short` | `long`)

### Encounter

#### `attack`
- Purpose: resolve a weapon/basic attack.
- Parameters:
	- `attack_id` (required, string)
	- `target_instance_ids` (required, string | string[]; single target or multiple targets)

#### `cast_spell`
- Purpose: resolve spell cast and resource consumption.
- Parameters:
	- `spell_id` (required, string)
	- `target_instance_ids` (required, string | string[])

#### `end_turn`
- Purpose: end actor's turn in encounter flow.
- Parameters: `{}` (none)

### Pre-game

#### `start`
- Purpose: move from lobby/pre-game to active run when setup is valid.
- Parameters: `{}` (none)

#### `create_player`
- Purpose: create player instance and add to party.
- Parameters:
	- `name` (required, string)
	- `description` (required, string)
	- `race` (required, string; race definition id)
	- `archetype` (required, string; archetype definition id)
	- `weapons` (required, string[]; weapon definition ids)
	- `entity_id` (optional, string; defaults to `player_<player_instance_id>`)
	- `player_instance_id` (optional, string; engine may auto-generate)

Legacy aliases accepted for compatibility and normalized by core:
- `race_id` -> `race`
- `archetype_id` -> `archetype`
- `weapon_ids` -> `weapons`

#### `remove_player`
- Purpose: remove player instance from party.
- Parameters:
	- `player_instance_id` (required, string)

#### `choose_dungeon`
- Purpose: select dungeon template for next run.
- Parameters:
	- `dungeon_id` (required, string)
	- `difficulty` (optional, enum `DifficultyType`: `easy` | `medium` | `hard`)

### Post-game

#### `finish`
- Purpose: close current run and return to pre-game state.
- Parameters: `{}` (none)

## Validation Rules

1. `type` must be a valid `ActionType` value.
2. `parameters` must contain all required keys for the selected action.
3. Unknown parameter keys should be ignored or rejected consistently (choose one engine policy).
4. Mode-gated actions must fail fast (e.g., `attack` outside encounter, `start` during encounter).
5. IDs must reference existing entities/templates before resolution.
6. Conversational actions should sanitize/trim `message` before processing.

## Minimal Examples

```json
{
	"type": "move",
	"actor_instance_id": "plr_inst_01",
	"parameters": { "destination_room_id": "room_hall_02" }
}
```

```json
{
	"type": "cast_spell",
	"actor_instance_id": "plr_inst_01",
	"parameters": {
		"spell_id": "spl_fire_bolt_01",
		"target_instance_ids": ["enm_inst_03"]
	}
}
```

```json
{
	"type": "converse",
	"actor_instance_id": "plr_inst_01",
	"parameters": {
		"message": "Can you guide us to the inner sanctum?",
		"target_instance_id": "npc_guardian_01",
		"tone": "friendly",
		"intent": "ask"
	}
}
```


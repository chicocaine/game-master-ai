# Game Master AI — Technical Documentation

> Detailed implementation reference covering architecture, game state, engine loops, LLM integration, and evaluation.

> Canonical gameplay rules are documented in `docs/RULES.md`; rule statements in this document must remain consistent with that file.

---

## Table of Contents

1. [Game Architecture](#1-game-architecture)
2. [Game–LLM Architecture](#2-gamelllm-architecture)
3. [Game States and Game Loops](#3-game-states-and-game-loops)
4. [LLM Integration and Context Management](#4-llm-integration-and-context-management)
5. [Separation of LLM Responsibilities](#5-separation-of-llm-responsibilities)
   - [5.1 Action Parser + CLARIFY](#51-action-parser)
   - [5.2 Query and Conversation Responder](#52-query-and-conversation-responder)
   - [5.3 Narration Generator](#53-narration-generator)
6. [Testing and Evaluation](#6-testing-and-evaluation)

---

## 1. Game Architecture

### 1.1 Overview

The system is a text-based dungeon crawler where an LLM acts as the Game Master (GM). The fundamental design contract is:

> **The LLM interprets player intent and emits structured `Action` objects. A deterministic engine resolves those actions and mutates game state. The LLM never directly mutates state.**

This separation of concerns means all game logic (combat math, rule enforcement, dungeon traversal) is fully reproducible and unit-testable without involving the LLM at all.

```
Player Input (natural language)
        │
        ▼
   [ LLM Agent ]  ← system context + game state summary
        │
        │  emits structured Action JSON
        ▼
  [ Validation Engine ]  ← rejects malformed / illegal actions
        │
        │  validated Action
        ▼
  [ Resolution Engine ]  ← deterministic: dice, rules, state mutation
        │
        │  emits Event stream
        ▼
  [ Narration LLM ]  ← turns event stream into narrative text
        │
        ▼
  Player Output (narrative + game state delta)
```

### 1.2 Directory Structure

| Path | Responsibility |
|------|----------------|
| `core/` | Deterministic game logic: `action.py`, `validation_engine.py`, `resolution_engine.py`, dice, rules, and state contracts |
| `engine/` | Execution infrastructure: `game_loop.py`, `state_manager.py`, low-level `llm_client.py`, and runtime orchestration |
| `agent/` | Decision layer: `agent_manager.py`, `player_parser.py`, `narrator.py`, `enemy_ai.py`, `context_builder.py`, and `memory.py` |
| `models/` | Typed dataclass models for all game objects |
| `registry/` | Data loaders and in-memory indexes for static game data |
| `data/` | JSON definitions for races, archetypes, weapons, spells, attacks, enemies, dungeons, status effects |
| `util/` | JSON schema validator, entity factory, logging helpers |
| `tests/` | Pytest test suites |

### 1.3 Data Model Relationships

```
Race ──────────────────────┐
  ├─ base_hp, base_AC,     │
  │  base_spell_slots      ├──► Entity (runtime instance)
  └─ archetype_constraints │        ├─ hp, AC, spell_slots (computed)
                           │        ├─ merged_attacks  (race + archetype + weapon + own)
Archetype ─────────────────┤        ├─ merged_spells   (race + archetype + weapon + own)
  ├─ hp_mod, AC_mod,       │        ├─ merged_resistances / immunities / vulnerabilities
  │  spell_slot_mod        │        └─ active_status_effects
  ├─ weapon_constraints    │
  └─ known_attacks/spells  │
                           │
 Weapon ───────────────────┘
  ├─ known_attacks
  └─ known_spells

Entity ◄── Player (player_instance_id)
       ◄── Enemy

Dungeon
  └─ rooms[] (Room)
       └─ encounters[] (Encounter)
            └─ enemies[] (Enemy)
```

**Key design decision — definition vs. instance:** Static JSON data files (e.g., `data/players.json`) contain *definition objects* identified by `id`. At runtime, a player is instantiated with a separate `player_instance_id`. This allows the same player template to be used multiple times or across sessions without collision.

### 1.4 Core Data Models

#### Entity
The base class for all combatants (`Player`, `Enemy`). Stats (HP, AC, spell slots) are computed from `Race` base values + `Archetype` modifiers at construction time. `merged_attacks`, `merged_spells`, `merged_resistances`, `merged_immunities`, and `merged_vulnerabilities` are computed properties that union and deduplicate contributions from the Race, Archetype, Weapon(s), and own known lists.

#### Archetype + Race Constraints
At instantiation, `Entity.create()` enforces two constraint checks:
- `_validate_archetype_constraint` — the archetype must appear in `race.archetype_constraints` (if constraints are set).
- `_validate_weapon_constraints` — each equipped weapon must satisfy the archetype's `WeaponConstraints` (proficiency, handling, weight class, delivery, magic type).

These are hard validation errors raised at entity creation time, not deferred to action resolution.

#### Dungeon
A node graph of `Room` objects connected by `room_id` references. Each `Room` holds zero or more `Encounter` objects. Encounters contain `Enemy` instances and a `difficulty`/`clear_reward`. Rooms track `is_visited`, `is_cleared`, and `is_rested` state flags, and expose `allowed_rests` (short / long).

#### Action
```python
@dataclass
class Action:
    type: ActionType          # enum — the resolved intent
    parameters: Dict[str, Any]
    actor_instance_id: str    # who is performing the action
    raw_input: str            # original player text (for logging / narration)
    reasoning: str            # LLM chain-of-thought (optional, for debugging)
    metadata: Dict[str, Any]
    action_id: str            # uuid
```

Required parameters per `ActionType` are declared in a single `REQUIRED_PARAMETERS` table in `core/action.py`, making validation trivially extensible.

#### Event
```python
@dataclass
class Event:
    type: EventType
    name: str
    payload: Dict[str, Any]   # event-specific data
    source: str               # "engine" | "gm" | "combat_engine" etc.
    timestamp: str            # UTC ISO 8601
    event_id: str             # uuid
```

Events are the single source of truth for everything that happened in a turn. The narration LLM consumes the event stream for a turn to produce player-facing text. The event log is also the audit trail for session replay and debugging.

#### Narration
```python
@dataclass
class Narration:
    event_id: str           # the event this narration describes
    text: str               # rendered narrative text
    source: str             # "game-master-ai"
    metadata: Dict[str, Any]
    timestamp: str
    narration_id: str
```

Narrations are 1-to-1 or 1-to-many with events. A single round of combat may produce many events (ATTACK_HIT, DAMAGE_APPLIED, STATUS_EFFECT_APPLIED) that are batched into one cohesive narration passage.

---

## 2. Game–LLM Architecture

### 2.1 Roles of the LLM

The LLM is called in four distinct roles that must remain clearly separated:

| Role | Input | Output | State mutation? |
|------|-------|--------|----------------|
| **Action Parser** | Player natural language + game context | Structured `Action` JSON or `Clarify` request | No |
| **Query/Conversation Responder** | Player question/dialogue + game context | Natural language reply | No |
| **Narration Generator** | Resolved `Event` stream | Narrative text (`Narration`) | No |
| **Enemy AI** | Encounter state summary + acting enemy details | Structured `Action` JSON | No |

All four roles are read-only with respect to game state. They receive a summary of current state as context, but only the deterministic resolution engine writes to state.

### 2.2 LLM Call Architecture

```
                        ┌──────────────────────────────┐
                        │        ContextBuilder        │
                        │  - game_state_summary()      │
                        │  - dungeon_summary()         │
                        │  - party_summary()           │
                        │  - rules_summary()           │
                        │  - encounter_summary()       │
                        └──────────────┬───────────────┘
                                       │ context dict
           ┌───────────────────────────┼──────────────────────┬──────────────────┐
           ▼                           ▼                      ▼                  ▼
   [ ActionParserLLM ]      [ ConversationLLM ]      [ NarrationLLM ]   [ EnemyAILLM ]
   system: rules +          system: world lore +     system: style +    system: rules +
           legal actions             party state             event schema       enemy persona
   user:   raw player input  user:   player message   user:  event list  user:  encounter state
                                                              JSON               + enemy details
   output: Action JSON        output: NPC/GM reply     output: narrative  output: Action JSON
           | Clarify JSON                                      + tone             + reasoning
```

### 2.3 Prompt Layer Responsibilities

Each LLM role uses a dedicated system prompt. The system prompt template files will live under `agent/prompts/`:

- `agent/prompts/action_parser.md` — strict JSON output schema, list of legal action types and their required parameters, game rules summary, few-shot examples, and the `CLARIFY` response schema for ambiguous input.
- `agent/prompts/conversation.md` — world/lore context, NPC persona instructions, tone guidelines.
- `agent/prompts/narration.md` — narrative style guide, event type vocabulary, output format rules (no stat numbers in fiction, etc.).
- `agent/prompts/enemy_ai.md` — legal encounter actions, enemy persona and behavioral instructions (aggressive, defensive, opportunistic), few-shot examples, JSON output schema.

### 2.4 Context Budget Management

Each LLM call receives a context payload assembled by `ContextBuilder`. The payload must remain within the model's context window. Strategies:

- **Game state summary** is a condensed flat dict, not raw model `to_dict()` output.
- **Dungeon summary** includes only the current room + adjacent rooms, not the full dungeon graph.
- **Party summary** shows only current HP, spell slots, active status effects, and available actions.
- **History window** for the conversation responder is capped at the last N turns (configurable, default 10).
- All context sections are individually token-estimated before assembly. If the total exceeds a configurable `max_context_tokens` budget, lower-priority sections (e.g., history) are truncated first.

---

## 3. Game States and Game Loops

### 3.1 Game States

The engine operates as a state machine. Legal transitions are enforced by the validation engine at action submission time.

```
         ┌──────────────────────────┐
         │         PRE_GAME         │  ◄── initial state
         │  - party setup           │
         │  - dungeon selection     │
         └───────────┬──────────────┘
                     │  ActionType.START (all constraints met)
                     ▼
         ┌──────────────────────────┐
    ┌───►│       EXPLORATION        │
    │    │  - move, explore, rest   │
    │    │  - converse, query       │
    │    └───────────┬──────────────┘
    │                │  encounter triggered on room entry
    │                ▼
    │    ┌──────────────────────────┐
    │    │        ENCOUNTER         │
    │    │  - attack, cast_spell    │
    │    │  - end_turn              │
    │    └───────────┬──────────────┘
    │                │  encounter cleared OR party wiped
    └────────────────┘  (back to EXPLORATION if cleared)
                     │  dungeon end_room reached and cleared
                     ▼
         ┌──────────────────────────┐
         │        POST_GAME         │
         │  - results, rewards      │
         │  - ActionType.FINISH     │
         └───────────┬──────────────┘
                     │  ActionType.FINISH
                     ▼
                  PRE_GAME  (loop)
```

`ActionType.ABANDON` and `ActionType.QUERY` and `ActionType.CONVERSE` are legal in every state.

### 3.2 Pre-Game Loop

**Purpose:** Build the party and select a dungeon before the run begins.

**Valid actions:** `create_player`, `remove_player`, `choose_dungeon`, `start`, `abandon`, `query`, `converse`

**`start` preconditions (enforced by validation engine):**
- At least one player in the party.
- A dungeon has been chosen (`dungeon_id` is set in game state).
- All players have valid race + archetype combinations (already enforced on creation).

**Loop:**
```
while state == PRE_GAME:
    raw_input = get_player_input()
    action = action_parser_llm(raw_input, context)
    errors = validate_action(action, game_state)
    if errors:
        emit EVENT(ACTION_REJECTED, {errors})
        continue
    game_state = resolve_pre_game_action(action, game_state)
    emit EVENT(ACTION_RESOLVED, {...})
    narration = narration_llm(events_this_turn)
    deliver_output(narration)
```

### 3.3 In-Game Loop

The in-game loop nests two sub-loops: **Exploration** and **Encounter**.

#### Exploration Sub-Loop

**Valid actions:** `move`, `explore`, `rest`, `converse`, `query`, `abandon`

```
while state == EXPLORATION:
    raw_input = get_player_input()
    action = action_parser_llm(raw_input, context)
    errors = validate_action(action, game_state)
    if errors:
        emit EVENT(ACTION_REJECTED, ...)
        continue
    events = resolve_exploration_action(action, game_state)
    emit events
    update_game_state(events)
    if current_room.has_active_encounter():
        transition_to(ENCOUNTER)
    if current_room.id == dungeon.end_room and current_room.is_cleared:
        transition_to(POST_GAME)
    narration = narration_llm(events)
    deliver_output(narration)
```

**Resolution details:**
- `move`: validates `destination_room_id` is connected to current room and requires the current room to be cleared before movement is allowed. Emits `ROOM_ENTERED`. Sets `is_visited = True`. If the destination room has uncleared encounters, transitions to ENCOUNTER.
- `explore`: reveals room details; emits `ROOM_EXPLORED`.
- `rest`: checks `room.allowed_rests` contains the requested `rest_type`. Short restores partial HP and partial spell slots. Long rest restores full HP and full spell slots and may revive a downed entity (`hp == 0`). Short rest cannot revive a downed entity. Emits `REST_STARTED` → `REST_COMPLETED`. Sets `room.is_rested = True` (prevents re-resting).

#### Encounter Sub-Loop (Turn-Based Combat)

**Valid actions:** `attack`, `cast_spell`, `end_turn`, `converse`, `query`, `abandon`

**Turn order:** Initiative is rolled (d20 + modifier) for all combatants at the start of each encounter. Turns proceed in descending initiative order.

```
on ENCOUNTER_STARTED:
    roll initiative for all combatants
    emit INITIATIVE_ROLLED for each
    set turn_order = sorted by initiative desc

while state == ENCOUNTER:
    current_actor = turn_order[current_turn_index]
    if current_actor is Player:
        raw_input = get_player_input()
        response = action_parser_llm(raw_input, context)
        if response.type == "clarify":
            deliver_output(response.question)   # ask player to disambiguate
            continue                             # re-prompt, do not advance turn
        action = response  # validated Action
        errors = validate_action(action, game_state)
        if errors: emit ACTION_REJECTED; continue
        events = resolve_encounter_action(action, game_state)
    else:  # Enemy turn — resolved by LLM
        encounter_context = build_encounter_context(current_actor, game_state)
        action = enemy_ai_llm(encounter_context)  # returns Action JSON
        errors = validate_action(action, game_state)
        if errors: action = fallback_enemy_action(current_actor)  # safe default
        events = resolve_encounter_action(action, game_state)

    emit events
    update_game_state(events)
    tick_status_effects(current_actor)

    if all enemies dead: transition_to(EXPLORATION), mark encounter cleared
    if all players dead: transition_to(POST_GAME) with defeat
    advance_turn()
    narration = narration_llm(events)
    deliver_output(narration)
```

**Enemy AI context payload** sent to `EnemyAILLM` per turn:
```json
{
  "acting_enemy": {
    "instance_id": "enm_inst_goblin_02",
    "name": "Goblin Skirmisher",
    "hp": 6,
    "max_hp": 10,
    "known_attacks": ["atk_dagger_stab_01", "atk_throw_rock_01"],
    "known_spells": [],
    "active_status_effects": [],
    "persona": "cowardly, opportunistic — prefers ranged attacks when outnumbered"
  },
  "encounter": {
    "enemies": [{"instance_id": "enm_inst_goblin_01", "hp": 0}, {"instance_id": "enm_inst_goblin_02", "hp": 6}],
    "players": [{"instance_id": "plr_inst_01", "name": "Araniel", "hp": 12, "AC": 14}]
  },
  "legal_actions": ["attack", "cast_spell", "end_turn"]
}
```

The `EnemyAILLM` responds with the same `Action` JSON schema as the player action parser. The `actor_instance_id` is set to the enemy's `instance_id`. If the response fails to parse or fails validation, `fallback_enemy_action` selects the first available attack targeting the lowest-HP player.

**Attack resolution:**
1. Roll attack: `d20 + hit_modifiers` vs. target `AC` or if attack difficulty class `DC` is greater than `0`, the `target_entity` will perform a `d20` saving throw. If the saving throw is equal to or greater than the difficulty class of the attack, the saving throw will succeed and the attack will fail.
2. On hit: roll damage using weapon/attack damage expression. Apply resistance/immunity/vulnerability multipliers.
3. Deduct HP. Emit `ATTACK_HIT` or `ATTACK_MISSED`, `DAMAGE_APPLIED`, `HP_UPDATED`, `DEATH` if applicable.
4. Apply `applied_status_effects` from the attack on hit.

**Spell resolution:** If spell difficulty class `DC` is `0`, the spell will succeed no matter what, else the `target_entity` will make a `d20` saving throw. AOE spells resolve against each target in `target_instance_ids`. Heal spells skip the hit roll. Emit `SPELL_CAST`, then per-target events.

**Status effect resolution:** DoT and HoT `StatusEffectType` are resolved every turn. Control `StatusEffectType` are checked at the start of each turn. AC modifier `StatusEffectType` update the entity's `AC` at application, and returns back to `base_AC` when the status effect is removed. Immunities, Resistances and Vulnerabilities are checked during damage resolutions. 

**Status effect tick:** At end of each actor's turn, the duration of all `active_status_effects` is decremented by 1. Effects at 0 are removed and `STATUS_EFFECT_REMOVED` is emitted.

### 3.4 Post-Game Loop

**Valid actions:** `finish`, `query`, `converse`, `abandon`

Summary stats are computed (enemies defeated, rooms cleared, damage dealt/received) and passed to the narration LLM for a closing passage. `ActionType.FINISH` resets game state to PRE_GAME.

---

## 4. LLM Integration and Context Management

### 4.1 LLM Client (`engine/llm_client.py`)

A thin wrapper around the model provider SDK (OpenAI-compatible API). Responsibilities:
- Sends system + user messages.
- Handles retries with exponential backoff on rate-limit or transient errors.
- Records raw request metadata (model, prompt token count, completion token count, latency) to a log entry for performance evaluation.
- Raises typed exceptions (`LLMParseError`, `LLMTimeoutError`) so callers can handle failure modes explicitly.

```python
@dataclass
class LLMRequest:
    system_prompt: str
    user_message: str
    model: str
    max_tokens: int
    temperature: float
    metadata: Dict[str, Any]   # caller-provided, passed through to log

@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    model: str
    request_id: str
```

### 4.2 Context Builder (`agent/context_builder.py`)

Assembles the context payload for each LLM call from current game state. Every section is individually estimated for token count. The builder enforces a total `max_context_tokens` budget by dropping lower-priority sections when over budget.

**Context sections by priority (highest → lowest):**

| Priority | Section | Contents |
|----------|---------|----------|
| 1 | `current_state` | Game state enum, current room id, turn index, round index |
| 2 | `party` | Per-player: name, hp/max_hp, spell_slots/max, active status effects, available actions |
| 3 | `current_room` | Room name, description, connections, encounter status |
| 4 | `rules_summary` | Legal actions for current state and their required parameters |
| 5 | `adjacent_rooms` | Name and id of connected rooms (for move action) |
| 6 | `encounter` | Enemy list with hp/max_hp, known attacks |
| 7 | `history` | Last N turn summaries (action + narration) |
| 8 | `world_lore` | Dungeon description, difficulty (static, lowest priority) |

Token estimation uses a simple character-count heuristic (`len(text) / 4`) unless a tokenizer is injected.

### 4.3 State Summary Format

The game state summary is a flat JSON object, not the full model `to_dict()` representation. Example:

```json
{
  "state": "exploration",
  "dungeon": "The Sunken Catacombs",
  "difficulty": "hard",
  "room": {
    "id": "room_crypt_01",
    "name": "The Broken Crypt",
    "description": "Damp stone walls, the smell of rot.",
    "connections": ["room_entrance_01", "room_altar_02"],
    "is_cleared": false,
    "allowed_rests": ["short"]
  },
  "party": [
    {
      "instance_id": "plr_inst_01",
      "name": "Araniel",
      "hp": 18,
      "max_hp": 24,
      "spell_slots": 2,
      "max_spell_slots": 3,
      "status_effects": ["poisoned(2)"],
      "available_actions": ["move", "explore", "rest", "attack", "cast_spell", "converse", "query", "abandon"]
    }
  ],
  "turn": 3
}
```

### 4.4 Conversation History

The action parser and narration LLM do **not** use conversation history — each call is stateless with a fresh system + user message.

The conversation/query responder maintains a rolling window of the last N player messages and GM replies as a `messages[]` array in the OpenAI chat format. Only `role: user` and `role: assistant` messages from the conversation role are included; system messages are always the fresh context-injected system prompt.

---

## 5. Separation of LLM Responsibilities

### 5.1 Action Parser

**File:** `agent/player_parser.py`

**Responsibility:** Convert raw player natural language into a validated `Action` object.

**System prompt contract:**
- Output must be either a single `Action` JSON object or a `Clarify` JSON object (see below).
- The prompt lists every legal `ActionType` for the current game state and their required parameters.
- Few-shot examples are included for ambiguous cases (e.g., "I attack the skeleton" → `{"type": "attack", "parameters": {"attack_id": "...", "target_instance_ids": ["..."]}, "reasoning": "..."}`). 
- The LLM must include a `reasoning` field (chain-of-thought), which is logged but not shown to the player.
- If the player intent cannot map to any legal action, the output must be `{"type": "query", "parameters": {"question": "<original input>"}}` as a safe fallback.
- If the intent is clear but the target or parameter is ambiguous (e.g., multiple entities share the same name), the output must be a `Clarify` object instead of an `Action`.

**CLARIFY response:** When the action parser cannot resolve a required parameter unambiguously from context — most commonly `target_instance_ids`, or `attacks` and `spells`, when multiple entities, spells, attacks, share the same name — it returns a `Clarify` object:

```json
{
  "type": "clarify",
  "question": "Which goblin do you mean? There are two: one near the door (wounded) and one by the altar (full health).",
  "ambiguous_field": "target_instance_ids",
  "candidates": ["enm_inst_goblin_01", "enm_inst_goblin_02"]
}
```

The engine delivers `question` to the player as a GM prompt without advancing the turn or emitting any game events. The player's next input is fed back through the action parser with the original intent retained in the context, allowing the LLM to resolve the disambiguation. This loop continues until a valid `Action` is produced or the player changes intent entirely.

**Ambiguity triggers** (non-exhaustive):
- Multiple living enemies share the same `name` and the player refers to them by name only.
- A spell or attack can target different counts (single vs. AOE) and the player didn't specify.
- `rest_type` is not specified and the room allows both short and long rest.

**Parsing pipeline:**
```
raw_input
    │
    ▼
PlayerParserLLM.parse(raw_input, context)
    │  returns raw JSON string
    ▼
json.loads()  → raises LLMParseError if not valid JSON
    │
    ├─ type == "clarify"  → return ClarifyResponse, re-prompt player (no turn advance)
    ▼
Action.from_dict()  → raises ValueError if ActionType unknown
    │
    ▼
validate_action(action)  → List[str] errors
    │
    ├─ errors → emit ACTION_REJECTED event, return none
    └─ no errors → emit ACTION_VALIDATED event, return Action
```

**Failure handling:** If the LLM output is not parseable JSON after N retries, an `ERROR` event is emitted and the engine re-prompts the same actor without advancing turn order.

### 5.2 Query and Conversation Responder

**Files:** `agent/agent_manager.py`, `agent/memory.py`

**Responsibility:** Handle `ActionType.QUERY` and `ActionType.CONVERSE` actions. These do not pass through deterministic action resolution — they are routed through the agent manager after action validation.

**QUERY:** The player asks for information (`scope`: `rules`, `state`, `dungeon`, `party`). The responder answers factually from the provided context without embellishment or invention. It must not assert game state facts not present in the context payload.

**CONVERSE:** In-world dialogue. The LLM plays the target NPC (or the GM narrator if no `target_instance_id`). Response style adapts to the `tone` and `intent` parameters. The conversation history window is active here.

**Key constraint:** The conversation responder must not emit or imply game-state changes (e.g., "The merchant gives you a sword"). Any actual state changes triggered by dialogue must be represented as a separate `Action` that goes through the engine.

### 5.3 Narration Generator

**File:** `agent/narrator.py`

**Responsibility:** Convert the resolved `Event` stream from a single turn into immersive narrative prose.

**Input to the LLM:** A JSON array of events from the current turn, each with `type`, `name`, and `payload`. The system prompt specifies:
- Write in second-person present tense ("You swing your longsword...").
- Do not expose raw stat numbers ("You deal 7 damage") unless contextually appropriate.
- Describe the mechanical outcome in fiction ("The skeleton staggers and collapses").
- If multiple events describe the same logical beat (e.g., ATTACK_HIT + DAMAGE_APPLIED + DEATH), merge them into a single sentence.
- Use event `source` field to attribute actions to the right actor.

**Batching:** Events from a full round (all combatants' turns) may be batched into a single narration call to produce a cohesive paragraph rather than one sentence per event.

**Narration metadata:** The LLM is asked to return a `tone` field alongside the text (`tense`, `mood` — e.g., `"tense"`, `"triumphant"`, `"ominous"`). This can be used by a front end to set background music or visual effects.

---

## 6. Testing and Evaluation

### 6.1 Functional Testing

Tests use `pytest` and are organized by module. All functional tests are deterministic — no LLM calls are made. LLM interactions are covered by separate evaluation harnesses (section 6.3 onward).

#### Existing Test Coverage

| File | Covers |
|------|--------|
| `tests/test_actions.py` | `Action` construction, parameter validation, `CONVERSE` trimming, `ATTACK`/`CAST_SPELL` target validation |
| `tests/test_events.py` | `Event` construction, serialization round-trip, factory helpers |
| `tests/test_narration.py` | `Narration` construction, validation |
| `tests/test_data_loader.py` | Registry load and ID resolution |
| `tests/test_player_enemy_models.py` | `Player`, `Enemy` creation, stat computation |
| `tests/test_entity_legacy.py` | `Entity.from_dict()` backwards compatibility |

#### Planned Test Modules

**`tests/test_engine_state.py`** — Game state machine transitions:
- State transitions are only triggered by legal actions.
- `start` is rejected if party is empty or no dungeon is selected.
- `move` is rejected if destination is not connected to current room.
- `rest` is rejected if room `allowed_rests` does not include the requested type or room is already rested.
- `attack` is rejected outside of ENCOUNTER state.

**`tests/test_resolution_combat.py`** — Deterministic combat resolution using a seeded `random.Random`:
- Hit roll above target AC → `ATTACK_HIT` emitted.
- Hit roll at or below target AC → `ATTACK_MISSED` emitted.
- Resistance halves damage (round down).
- Immunity results in zero damage.
- Vulnerability doubles damage.
- Entity HP reaching 0 → `DEATH` event emitted.
- Status effect duration decrement and removal.

**`tests/test_resolution_exploration.py`**:
- `move` to a connected room sets `is_visited` and emits `ROOM_ENTERED`.
- `move` to unconnected room is rejected.
- `rest` on a long-rest-allowed room restores full HP and spell slots.
- `rest` in an already-rested room is rejected.
- Entering a room with an active encounter transitions state to ENCOUNTER.

**`tests/test_entity_constraints.py`**:
- Archetype not in `race.archetype_constraints` raises `ValueError` at creation.
- Weapon violating archetype `weapon_constraints` raises `ValueError` at creation.
- `merged_attacks` deduplicates by `id`.

**`tests/test_dice.py`**:
- `parse_dice_notation` handles `NdX`, `NdX+M`, `NdX-M`.
- `roll_dice` with seeded RNG is reproducible.
- Invalid notation raises `ValueError`.

**`tests/test_action_parser_integration.py`** *(uses real or mock LLM)*:
- Parser output for canonical player phrases resolves to the expected `ActionType`.
- Malformed LLM JSON triggers `LLMParseError` and graceful fallback.
- Out-of-context actions are rejected by `validate_action`.

#### Test Case Fixtures

Static test fixtures live in `tests/fixtures/`. Each fixture is a JSON file that can be loaded by registry helpers:

- `fixtures/party_single_player.json` — one player with known race, archetype, weapons.
- `fixtures/dungeon_simple.json` — two-room dungeon with one encounter.
- `fixtures/encounter_single_enemy.json` — one skeleton enemy.
- `fixtures/game_state_exploration.json` — full game state snapshot in EXPLORATION state.
- `fixtures/game_state_encounter.json` — full game state snapshot mid-combat with initiative set.

#### Running Tests

```bash
pytest tests/ -v
pytest tests/test_resolution_combat.py -v --tb=short       # combat only
pytest tests/ -k "not integration" -v                       # skip LLM integration tests
```

### 6.2 Performance Evaluation

Performance metrics are recorded per `LLMResponse` and stored to a JSONL log file (`logs/llm_performance.jsonl`). Each record contains:

```json
{
  "request_id": "uuid",
  "role": "action_parser | conversation | narration",
  "model": "gpt-4o-mini",
  "timestamp": "2026-03-01T14:23:00Z",
  "prompt_tokens": 812,
  "completion_tokens": 94,
  "total_tokens": 906,
  "latency_ms": 1340,
  "game_state": "encounter",
  "success": true,
  "parse_error": false
}
```

#### Response Time

Target latency budgets per role (wall-clock time to first complete response):

| Role | Target P50 | Target P95 |
|------|-----------|-----------|
| Action Parser | < 1.5 s | < 3 s |
| Conversation Responder | < 2 s | < 4 s |
| Narration Generator | < 2.5 s | < 5 s |

Streaming responses (SSE / token streaming) should be used for the narration generator so text can begin rendering before the full completion arrives.

#### Token Usage Estimation

Token counts are estimated during context assembly using the `len(text) / 4` heuristic before the call is made, then reconciled against the provider's actual reported counts after the call. The delta is logged to track heuristic accuracy. Estimation is used to enforce `max_context_tokens` budget gates.

Per-session token totals are summed across all `LLMResponse` records in a session.

#### Cost Analysis

Cost is computed post-session from the token log. A `CostEstimator` utility (`util/cost_estimator.py`) holds a configurable price table:

```python
PRICE_TABLE = {
    "gpt-4o": {"input": 2.50, "output": 10.00},       # USD per 1M tokens
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
}
```

Cost is reported as: total cost per session, cost per role, cost per turn, and projected cost per 10-room dungeon run. This informs model selection per role — e.g., using a cheaper model for action parsing and a more capable model for narration.

### 6.3 LLM Accuracy Evaluation

LLM quality is evaluated offline against a static **golden dataset** (`tests/eval/golden_actions.jsonl`). Each record is:

```json
{
  "id": "case_001",
  "game_state": "encounter",
  "party_context": { "...": "..." },
  "raw_input": "I slash at the orc with my sword",
  "expected_action_type": "attack",
  "expected_parameters": {
    "attack_id": "atk_longsword_slash_01",
    "target_instance_ids": ["enm_inst_orc_01"]
  },
  "tags": ["combat", "unambiguous"]
}
```

**Accuracy metrics:**

| Metric | Definition |
|--------|-----------|
| `action_type_accuracy` | % of cases where `action.type` matches `expected_action_type` |
| `parameter_exact_match` | % of cases where all expected parameters match exactly |
| `parameter_partial_match` | % of cases where at least the required parameters are present and correct |
| `parse_success_rate` | % of LLM responses that produced valid JSON parseable by `Action.from_dict()` |
| `validation_pass_rate` | % of parsed actions that pass `validate_action()` with no errors |

The eval runner (`tests/eval/run_eval.py`) iterates the golden dataset, calls the action parser LLM (or a mock), and computes these metrics. Results are written to `logs/eval_results.jsonl`.

A threshold gate for CI (when LLM calls are affordable in CI): `action_type_accuracy >= 0.90`, `parse_success_rate >= 0.98`.

### 6.4 Coherence and Relevance

These metrics apply to both the narration generator and the conversation responder. They are evaluated by a secondary **judge LLM** (or human review) against the same golden dataset extended with `expected_events` → `expected_narration_themes`.

| Metric | Method | Definition |
|--------|--------|-----------|
| **Coherence** | Judge LLM scoring (1–5) | Does the narration form coherent, grammatically correct prose? Does it logically follow from the events? |
| **Relevance** | Judge LLM scoring (1–5) | Does the narration address all events in the turn? Are there fabricated events not in the input? |
| **Tone consistency** | Keyword / sentiment match | Does the narration tone match the event severity (e.g., DEATH should not be narrated as comedic)? |
| **Conversation groundedness** | Fact-check against context payload | Does the conversation responder's answer contain only facts present in the context? |

Scores are logged to `logs/eval_quality.jsonl` per run.

### 6.5 Hallucination Detection

Hallucinations in this system take two specific forms:

**Type 1 — State hallucination:** The narration or conversation responder describes a game state fact (e.g., "your HP is full", "you have 5 spell slots", "the room to the north is unlocked") that is not consistent with the provided context payload. Detected by:
- Extracting entity references and numeric claims from the LLM output using a second LLM pass or regex patterns.
- Cross-checking each claim against the context payload that was provided.
- Flagging discrepancies as `hallucination_type: "state"`.

**Type 2 — Action hallucination:** The action parser emits an `Action` referencing an `attack_id`, `spell_id`, `entity_id`, or `room_id` that does not exist in the current game state or registry. Detected deterministically:
- Post-parse validation checks all ID references against the active registry and game state.
- These are caught as validation errors in `validate_action()` and emitted as `ACTION_REJECTED` events, so they do not reach the resolution engine.

**Hallucination rate metric:**

```
hallucination_rate = hallucinated_claims / total_verifiable_claims
```

Tracked per session in `logs/eval_quality.jsonl`. Target: `< 0.05` (fewer than 5% of verifiable claims are hallucinated).

**Mitigation strategies:**
- Explicit instruction in system prompts: "Only describe events present in the event list. Do not invent outcomes."
- Context grounding: all verifiable facts (HP values, room names, spell IDs) are explicitly present in the context payload.
- Temperature: action parser uses `temperature=0.0` for determinism; narration uses `temperature=0.7` for variety but bounded by the event input.
- Post-generation validation for action IDs (deterministic, no LLM required).

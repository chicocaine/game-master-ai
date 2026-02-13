# GameMasterAI – Game Design Document (GDD-lite)

## 1. Overview

**GameMasterAI** is a text-based, node-driven tabletop dungeon game managed by an AI agent. The agent interprets natural language commands, maintains game state, enforces rules, resolves combat, and narrates outcomes. The system is designed as a goal-directed AI agent operating within a constrained, rule-based environment.

---

## 2. Design Goals

* Demonstrate AI **agent-environment interaction**
* Use NLP for command interpretation and narration
* Keep mechanics deterministic and explainable
* Be fully playable and demoable within 2–3 weeks

---

## 3. Game Structure

### 3.1 Game Mode

* Single-party, PvE
* Turn-based combat encounters
* Text-based interaction via single shared input interface
* Node-based dungeon exploration
* Party moves as a collective unit during exploration

### 3.2 Party Size

* 1–4 players
* Downed/dead players remain part of the party during exploration but cannot take actions during combat

---

## 4. Core Systems

### 4.1 Dungeon & Exploration

* Dungeon is represented as a **node graph**
* Each node (room) has:

  * Description
  * Connected rooms
  * Optional encounter
  * Rest permission

**Exploration Rules**:

* Players may move only between connected rooms
* Exploration is free-form (not turn-based)
* Combat switches the system into Encounter Mode
* Room descriptions auto-narrate only on first visit; repeat visits are brief unless asked
* Rooms with encounters auto-start combat when first entered

---

## 5. Combat System

### 5.1 Initiative

* Initiative is rolled at the start of each encounter for each entity
* Entities include all living players and all enemies
* Downed/dead players do **not** participate in initiative
* Initiative order is fixed for the encounter duration

### 5.2 Turn Flow

1. Start of turn
2. Resolve start-of-turn status effects
3. Check if entity is stunned or incapacitated (skip turn if so)
4. Active entity performs **one valid action**
5. End of turn (apply end-of-turn effects)
6. Advance to next entity in initiative order
7. Increment round when initiative cycles

---

## 6. Character Model

### 6.1 Player Stats

* Name
* Race / Class
* HP / Max HP
* Armor Class (AC)
* Attack Modifier
* Known Attacks
* Spell Slots
* Known Spells
* Status Effects

### 6.2 Enemy Stats

* Name
* Race / Class
* HP / Max HP
* AC
* Attack Modifier
* Known Attacks
* Spell Slots
* Known Spells
* Status Effects

---

## 7. Action Types

### 7.1 Basic Actions

* Attack (different attacks can have different dice rolls or effects)
* Cast Spell
* End Turn
* Rest (outside combat or if room has no encounters left only)

### 7.2 Attack Resolution

* Roll d20 + attack modifier
* Hit if result ≥ target AC
* On hit, roll damage (based on spell or attack specifications/rules)

---

## 8. Spell System

### 8.1 Spell Slots

* Casters have a limited number of spell slots
* Casting a spell consumes 1 slot
* Spell slots reset:

  * Partially on Short Rest
  * Fully on Long Rest

### 8.2 Spell Categories

#### Damage Spells

* Deal fixed dice-based damage

#### Healing Spells

* Restore HP to target

#### Status Effect Spells

* Apply status effects with duration

**Cleanse Effect Spells**

* Cleanse negative or positive status effects

#### AoE Spells

* Affect all valid targets in the encounter
* No spatial calculations

---

## 9. Status Effects

### 9.1 Supported Statuses

#### Stunned

* Effect: Skip entity’s turn
* Duration decreases each skipped turn

#### Poisoned

* Effect: Take damage at start of turn
* Duration decreases each turn

#### Burned

* Effect: Take damage at start of turn
* Duration decreases each turn

#### Weakened

* Negative attack modifier

#### Strengthened

* Positive attack modifier

#### Shielded/Fortified
* Positive AC modifier
* Duration decreases each turn

#### Vulnerable
* Negative AC modifier
* Duration decreases each turn

Status effects are resolved deterministically by the rule engine.
---

## 10. Rest System

### 10.1 Short Rest

* Allowed only in designated rooms
* Restores 25% HP and limited spell slots

### 10.2 Long Rest

* Allowed only in designated rooms
* Restores/Revives all player HP and spell slots

---

## 11. Win & Loss Conditions

### 11.1 GAME_COMPLETE

* Party reaches and exits through the dungeon exit node
* Dungeon is fully cleared

### 11.2 GAME_OVER (Defeat)

* All players reduced to 0 HP during an encounter
* Party cannot proceed further

### 11.3 Encounter Victory (Local)

* All enemies in the current encounter are defeated
* Party returns to exploration mode and continues dungeon progression
* Party receives reward points/coins (specified per encounter)

---

## 12. AI Agent Responsibilities

The AI agent:

* Interprets player commands (NLP)
* Maps intent to structured actions
* Validates actions against game rules
* Decides enemy actions and reasoning
* Applies game rules deterministically
* Updates game state
* Narrates outcomes
* Handles fallback logic for unclear inputs

The agent does **not**:

* Override deterministic rules
* Fudge dice rolls
* Bypass validation logic
* Modify game state except through valid action resolution

---

## 13. NLP Strategy and Agent Decision Making

### 13.1 Input Processing Pipeline

1. **Receive raw player input** – Text command from shared interface
2. **Intent Recognition** – LLM identifies intent (move, attack, cast_spell, rest, explore, end_turn)
3. **Entity/Target Extraction** – Identify which room, entity, or spell is referenced
4. **Action Mapping** – Convert parsed intent to structured Action object
5. **Validation** – Check action legality
6. **Resolution** – Execute action and update state
7. **Narration** – LLM generates descriptive output

**Info/Query Handling:**

If the input is a question (e.g., "where am I", "what rooms connect"), the LLM may return
`action: null` with a narration-only response. This avoids forcing an invalid action.

### 13.2 Intent Parsing and Fallback Logic

**Clear Intent Recognition:**

When player input is unambiguous, the LLM directly maps to an action:

* "Move east" → `move` to appropriate connected room
* "Attack the goblin" → `attack` targeting that enemy
* "Cast fire bolt on the mage" → `cast_spell` with specific target

**Ambiguous or Incomplete Intent:**

When input is unclear or incomplete, the system applies fallback logic:

1. **Partial Clarification** – Agent narrates what it understood and asks for missing info
   * Example: Player: "Attack the..." → Agent: "Which enemy? The goblin or the mage?"

2. **Fuzzy Matching** – If only one valid target exists, assume it
   * Example: Only one enemy present → assume it's the target

3. **Default Actions** – If intent is too vague, offer options
   * Example: Player: "Do something" → Agent: "You can move, attack, cast a spell, or end your turn. What'll it be?"

4. **Retry Logic** – After clarification, accept next input without re-querying

**Invalid Intent:**

If the LLM cannot parse intent (nonsensical input):

* Agent narrates a witty rejection and reprompts
* Example: Player: "Polymorph into a dragon" → Agent: "That's not something you can do here. Available actions: attack, cast spell, end turn, or explore."

### 13.3 Enemy AI Decision Making

**Enemy Turn Processing:**

When it's an enemy's turn, the LLM reasons through the decision:

1. **Assess current state** – Analyze enemy HP, party HP, status effects, available spells/attacks
2. **Evaluate options** – What actions are available?
3. **Make tactical decision** – Choose action based on simple heuristics:
   * Target lowest HP enemy if attacking
   * Use crowd control if multiple players are alive
   * Use healing if own HP is low
   * Prioritize threats (healers, high-damage dealers)
4. **Log reasoning** – Combat log includes reasoning for transparency
5. **Resolve action** – Apply damage/effects as normal

**Example Enemy Turn Log:**

```
Skeleton Mage's turn.
[AI Reasoning: I have 8 HP left. Arin has 18 HP. I have poison_cloud available. 
I'll cast it to affect both Arin and reduce incoming damage.]
Skeleton Mage casts Poison Cloud!
Arin is afflicted with Poisoned (2 turns).
```

### 13.4 Recommended LLM Configuration

**Model**: Claude or GPT-4 (or equivalent)

**System Prompt Guidelines**:

* Strict adherence to game rules
* Generate intent, not suggestions ("I detect attack intent", not "You should attack")
* Concise, punchy narration
* Deterministic reasoning for enemy decisions (show reasoning in combat log)

**Temperature**: 0.3–0.5 (low, for consistent rule application)

**Context Provided to LLM**:

* Current game state (mode, rooms, entities, initiative, combat log)
* Current turn status (whose turn, what actions are available)
* Grammar/examples of valid action structures

---

## 13. Game States and State Management

This section defines how the game maintains and transitions between different states. Clear state separation allows the AI agent to reason correctly and enforce valid actions.

### 13.1 Global Game State

The **Global Game State** exists at all times and represents the overall progress of the game outside of combat. It is the primary world state the AI agent reasons over when not in an encounter.

---

#### 13.1.1 GlobalGameState Schema (Conceptual)

```json
{
  "game_mode": "exploration", 
  "current_dungeon_id": "dungeon_01",
  "current_room_id": "room_entrance",

  "party": {
    "players": [
      {
        "entity_id": "player_1",
        "name": "Arin",
        "race": "Elf",
        "class": "Wizard",
        "hp": 18,
        "max_hp": 18,
        "ac": 12,
        "attack_modifier": 2,
        "known_attacks": ["staff_strike"],
        "spell_slots": {
          "current": 3,
          "max": 3
        },
        "known_spells": ["fire_bolt", "sleep"],
        "status_effects": []
      }
    ]
  },

  "cleared_encounters": ["encounter_001"],

  "dungeon_state": {
    "visited_rooms": ["room_entrance"],
    "rested_rooms": []
  },

  "progression": {
    "total_rewards": 0,
    "encounters_cleared": 0
  }
}
```

---

#### 13.1.2 Field Explanations

* **game_mode**: Determines whether the system is in `exploration` or `encounter` mode
* **current_dungeon_id**: Identifier for the active dungeon
* **current_room_id**: The room/node the party currently occupies

**party.players**:

* Represents all player-controlled entities
* Uses the same base entity structure as enemies
* Entity data persists across encounters

**cleared_encounters**:

* List of encounter IDs already resolved
* Prevents encounters from re-triggering

**dungeon_state**:

* Tracks exploration-level metadata
* `visited_rooms`: Used for narration or fog-of-war logic
* `rested_rooms`: Prevents repeated rest abuse in the same room

**progression**:

* Tracks session rewards and achievements
* `total_rewards`: Cumulative points/coins earned from encounters
* `encounters_cleared`: Number of encounters defeated

---

#### 13.1.3 Responsibilities of GlobalGameState

The GlobalGameState is responsible for:

* Determining whether movement between rooms is valid
* Checking if entering a room triggers an encounter
* Enforcing rest rules
* Providing world context to the AI agent during exploration

---

### 13.2 Dungeon Entry Point

Each dungeon has a designated **entry node**, representing the entrance of the dungeon.

**Rules:**

* The game always starts at the dungeon entry node
* The entry node establishes the initial Global Game State
* The entry node may or may not contain an encounter

---

### 13.3 Encounter (Battle) State

The **Encounter State** is a temporary, turn-based state created when the party enters a room containing an unresolved encounter. It exists only while combat is active and is destroyed once the encounter ends.

---

#### 13.3.1 EncounterState Schema (Conceptual)

```json
{
  "encounter_id": "encounter_002",
  "room_id": "room_crypt",
  "round": 1,

  "entities": [
    {
      "entity_id": "player_1",
      "type": "player",
      "hp": 18,
      "max_hp": 18,
      "ac": 12,
      "attack_modifier": 2,
      "known_attacks": ["staff_strike"],
      "spell_slots": {
        "current": 3,
        "max": 3
      },
      "known_spells": ["fire_bolt", "sleep"],
      "status_effects": []
    },
    {
      "entity_id": "enemy_1",
      "type": "enemy",
      "name": "Skeleton Mage",
      "hp": 14,
      "max_hp": 14,
      "ac": 11,
      "attack_modifier": 3,
      "known_attacks": ["bone_strike"],
      "spell_slots": {
        "current": 2,
        "max": 2
      },
      "known_spells": ["poison_cloud"],
      "status_effects": []
    }
  ],

  "initiative_order": ["player_1", "enemy_1"],
  "active_entity_id": "player_1",

  "combat_log": [
    "Combat begins!",
    "Arin wins initiative."
  ]
}
```

---

#### 13.3.2 Field Explanations

* **encounter_id**: Unique identifier for the encounter
* **room_id**: Room in which the encounter takes place
* **round**: Current combat round number

**entities**:

* All combat participants (players and enemies)
* Uses the same base entity structure
* Entity data here is a *snapshot* copied from GlobalGameState

**initiative_order**:

* Fixed order of entity turns for the encounter

**active_entity_id**:

* Indicates whose turn it currently is

**combat_log**:

* Append-only narration and resolution log
* Used for UI display and debugging

---

#### 13.3.3 Encounter Turn Resolution Rules

Each turn follows this deterministic sequence:

1. Start of turn
2. Resolve start-of-turn status effects
3. Check for skipped turn (e.g., stunned)
4. Active entity performs **one valid action**
5. End of turn
6. Advance to next entity in initiative order
7. Increment round when initiative cycles

---

#### 13.3.4 Responsibilities of EncounterState

The EncounterState is responsible for:

* Enforcing turn order and valid actions
* Applying damage, healing, and status effects
* Updating spell slots and HP
* Detecting victory or defeat
* Producing combat narration

Once the encounter ends, relevant changes (HP, spell slots, statuses) are synchronized back to the GlobalGameState.

---

### 13.4 State Transitions

**Exploration → Encounter**

* Trigger: Party enters a room with an unresolved encounter
* Action: Generate Encounter State and roll initiative

**Encounter → Exploration**

* Trigger: All enemies defeated
* Action: Mark encounter as cleared and return to exploration mode

**Exploration → Exploration**

* Trigger: Movement between rooms or resting

---

### 13.5 Action Validity by State

**Exploration Mode**:

* Move between connected rooms
* Explore room
* Rest (if allowed)

**Encounter Mode**:

* Attack
* Cast spell
* End turn

Invalid actions are rejected by the rule engine with a narrated explanation.

---

## 14. Agent Action Model

This section also serves as the **formal specification for Action Models**. Each action represents a discrete, validated state transition that the engine can apply deterministically.

This section defines how the AI agent interprets player input, maps it to structured actions, validates those actions against the current game state, and executes them.

The Agent Action Model serves as the bridge between **natural language input** and **deterministic rule execution**.

---

### 14.1 Action Pipeline Overview

Each player input is processed through the following pipeline:

1. **Input Parsing (NLP)** – Interpret player intent from natural language
2. **Action Mapping** – Convert intent into a structured action object
3. **Action Validation** – Check action legality based on current game state
4. **Action Resolution** – Apply game rules and update state
5. **Narration** – Generate descriptive output

---

### 14.2 Base Action Object Schema

All actions are converted into a structured format before execution.

```json
{
  "actor_id": "player_1",
  "action_type": "attack",
  "target_id": "enemy_1",
  "parameters": {
    "attack_id": "staff_strike",
    "spell_id": null
  }
}
```

**Fields:**

* **actor_id**: Entity performing the action
* **action_type**: One of `move`, `attack`, `cast_spell`, `rest`, `end_turn`, `explore`
* **target_id**: Optional target entity or room
* **parameters**: Action-specific metadata

---

### 14.3 Action Models (By Type)

Each action model is formally defined below using a **conceptual schema**. These schemas specify the exact data the engine expects after intent parsing, enabling deterministic validation and resolution.

---

#### 14.3.1 Move Action

**Purpose:** Transition the party between connected dungeon nodes during exploration.

**Schema (Conceptual):**

```json
{
  "actor_id": "player_1",
  "action_type": "move",
  "target_id": "room_hallway",
  "parameters": {}
}
```

**Validation Rules:**

* Only valid in `exploration` mode
* Target room must be connected to `current_room_id`

**State Effects:**

* Updates `current_room_id`
* Marks room as visited
* May trigger encounter creation

---

#### 14.3.2 Attack Action

**Purpose:** Perform a physical or basic attack against a single target during combat.

**Schema (Conceptual):**

```json
{
  "actor_id": "player_1",
  "action_type": "attack",
  "target_id": "enemy_1",
  "parameters": {
    "attack_id": "staff_strike"
  }
}
```

**Validation Rules:**

* Only valid in `encounter` mode
* Actor must be the active entity
* Target must be alive

**State Effects:**

* Resolve hit roll and damage
* Update target HP

---

#### 14.3.3 Cast Spell Action

**Purpose:** Cast a known spell during combat.

**Schema (Conceptual):**

```json
{
  "actor_id": "player_1",
  "action_type": "cast_spell",
  "target_id": "enemy_1",
  "parameters": {
    "spell_id": "fire_bolt"
  }
}
```

**Validation Rules:**

* Only valid in `encounter` mode
* Actor must be the active entity
* Spell must be known and spell slots available

**State Effects:**

* Consume spell slot
* Apply damage, healing, or status effects

---

#### 14.3.4 End Turn Action

**Purpose:** End the active entity’s turn.

**Schema (Conceptual):**

```json
{
  "actor_id": "player_1",
  "action_type": "end_turn",
  "parameters": {}
}
```

**Validation Rules:**

* Only valid in `encounter` mode
* Actor must be the active entity

**State Effects:**

* Advance initiative order

---

#### 14.3.5 Rest Action

**Purpose:** Recover HP and spell slots outside of combat.

**Schema (Conceptual):**

```json
{
  "actor_id": "player_1",
  "action_type": "rest",
  "parameters": {
    "rest_type": "short"
  }
}
```

**Validation Rules:**

* Only valid in `exploration` mode
* Room must allow resting

**State Effects:**

* Restore HP and spell slots according to rest type
* Update `rested_rooms`

---

#### 14.3.1 Move Action

**Purpose:** Transition the party between connected dungeon nodes during exploration.

**Required Fields:**

* `actor_id`
* `action_type: "move"`
* `target_id` (room_id)

**Validation Rules:**

* Only valid in `exploration` mode
* Target room must be connected to current room

**State Effects:**

* Updates `current_room_id`
* May trigger encounter state creation

---

#### 14.3.2 Attack Action

**Purpose:** Perform a physical or basic attack against a single target during combat.

**Required Fields:**

* `actor_id`
* `action_type: "attack"`
* `target_id` (entity_id)
* `parameters.attack_id`

**Validation Rules:**

* Only valid in `encounter` mode
* Actor must be the active entity
* Target must be alive

**State Effects:**

* Resolves hit check and damage
* Updates target HP

---

#### 14.3.3 Cast Spell Action

**Purpose:** Cast a known spell during combat.

**Required Fields:**

* `actor_id`
* `action_type: "cast_spell"`
* `target_id` (entity_id or null for AoE)
* `parameters.spell_id`

**Validation Rules:**

* Only valid in `encounter` mode
* Actor must have available spell slots
* Spell must be known by the actor

**State Effects:**

* Consumes spell slot
* Applies damage, healing, or status effects

---

#### 14.3.4 End Turn Action

**Purpose:** Explicitly end the active entity’s turn.

**Required Fields:**

* `actor_id`
* `action_type: "end_turn"`

**Validation Rules:**

* Only valid in `encounter` mode
* Actor must be the active entity

**State Effects:**

* Advances initiative order

---

#### 14.3.5 Rest Action

**Purpose:** Recover HP and spell slots outside of combat.

**Required Fields:**

* `actor_id`
* `action_type: "rest"`
* `parameters.rest_type` (`short` or `long`)

**Validation Rules:**

* Only valid in `exploration` mode
* Room must allow resting

**State Effects:**

* Restores HP and spell slots based on rest type
* Updates `rested_rooms`

---

### 14.4 Supported Actions by Game Mode

#### Exploration Mode Actions

| Action  | Description                  |
| ------- | ---------------------------- |
| move    | Move to a connected room     |
| explore | Inspect the current room     |
| rest    | Perform a short or long rest |

#### Encounter Mode Actions

| Action     | Description            |
| ---------- | ---------------------- |
| attack     | Perform a basic attack |
| cast_spell | Cast a known spell     |
| end_turn   | End the current turn   |

---

### 14.5 Action Validation Rules

Before execution, each action is validated against the current state.

**Common Validation Checks:**

* Actor exists and is alive
* Action is allowed in the current `game_mode`
* Actor is the active entity (in encounters)

**Exploration-Specific Checks:**

* Target room is connected
* Resting is allowed in the room

**Encounter-Specific Checks:**

* Actor is not stunned or incapacitated
* Target is valid and alive
* Spell slots are available for spell casting

Invalid actions are rejected with a narrated explanation.

---

### 14.6 Intent-to-Action Mapping Examples

| Player Input                 | Parsed Intent | Action Object     |
| ---------------------------- | ------------- | ----------------- |
| "Go to the next room"        | move          | move → room_id    |
| "Attack the skeleton"        | attack        | attack → enemy_id |
| "Cast fire bolt on the mage" | cast_spell    | spell_id + target |
| "End my turn"                | end_turn      | end_turn          |

---

### 14.7 Agent Boundaries

The AI agent:

* Interprets intent
* Selects valid actions
* Narrates outcomes

The AI agent does **not**:

* Modify rules
* Fudge dice rolls
* Override validation logic

This ensures the system remains deterministic and explainable.

---

## 15. Sample Playthrough (User Experience Validation)

This section illustrates a short, representative gameplay sequence to validate the intended user experience, narration style, and action flow. The example demonstrates a single encounter lasting several turns.

---

### Scenario Setup

* **Player**: Arin, Elf Wizard (HP: 18, Spell Slots: 3)
* **Enemy**: Skeleton Mage (HP: 14, Spell Slots: 2)
* **Location**: Room – Ancient Crypt
* **Initiative Order**: Arin → Skeleton Mage

---

### Turn 1 – Arin

**Player Input:**

> "I cast Fire Bolt on the skeleton."

**Parsed Action:**

* Action: `cast_spell`
* Spell: `fire_bolt`
* Target: `enemy_1`

**Resolution & Narration:**

* Arin hurls a bolt of fire at the Skeleton Mage.
* Attack roll succeeds.
* The spell deals **6 fire damage**.

**State Update:**

* Skeleton Mage HP: 14 → 8
* Arin Spell Slots: 3 → 2

---

### Turn 1 – Skeleton Mage

**Enemy Action Decided by AI:**

* Casts `poison_cloud` (AoE)

**Resolution & Narration:**

* A sickly green mist spreads through the crypt.
* Arin is afflicted with **Poisoned (2 turns)**.

**State Update:**

* Arin gains Poisoned status

---

### Turn 2 – Arin

**Start of Turn:**

* Poisoned triggers: Arin takes **2 poison damage**.

**Player Input:**

> "Attack it with my staff."

**Parsed Action:**

* Action: `attack`
* Attack: `staff_strike`
* Target: `enemy_1`

**Resolution & Narration:**

* Arin strikes the Skeleton Mage with his staff.
* The attack hits, dealing **3 damage**.

**State Update:**

* Skeleton Mage HP: 8 → 5

---

### Turn 2 – Skeleton Mage

**Enemy Action Decided by AI:**

* Attempts a `bone_strike` attack.

**Resolution & Narration:**

* The Skeleton Mage lunges forward, but its attack misses.

---

### Turn 3 – Arin

**Start of Turn:**

* Poisoned triggers: Arin takes **2 poison damage**.
* Poisoned duration expires.

**Player Input:**

> "Cast Fire Bolt again."

**Resolution & Narration:**

* Flames erupt from Arin’s hand.
* The fire bolt strikes true, dealing **7 damage**.

**State Update:**

* Skeleton Mage HP: 5 → 0

---

### Encounter Resolution

**Narration:**

* The Skeleton Mage collapses into a pile of scorched bones.
* Combat ends. Victory!

**Post-Encounter State:**

* Encounter marked as cleared
* Party returns to Exploration Mode
* Updated HP and spell slots persist into GlobalGameState

---

This playthrough demonstrates:

* Natural language → structured action mapping
* Deterministic rule resolution
* Clear turn-based flow
* Concise but flavorful narration

---

## 28. Error Handling and Validation

This section defines how the system handles malformed input, impossible game states, and data corruption scenarios.

---

### 28.1 Input Validation Errors

**Malformed Commands:**

* **Empty input** – User submits blank text
  * Response: "I didn't catch that. Please try again."
  
* **Non-text input** – User submits invalid characters or gibberish
  * Response: Agent attempts fuzzy parsing; if unrecoverable, reprompt
  
* **Excessively long input** – Command exceeds reasonable length (e.g., >500 chars)
  * Response: "That's too long to parse. Try a shorter command."

**Intent Parsing Failures:**

* **Ambiguous target** – "Attack the one over there" with multiple valid targets
  * Response: Clarification prompt listing valid targets
  
* **Unknown spell/attack** – "Cast Meteor Storm" but no such spell exists
  * Response: "You don't know that spell. Known spells: [list]"
  
* **Invalid action for game mode** – "Attack the skeleton" during exploration
  * Response: "You can't attack outside of combat. You can move, explore, or rest."

---

### 28.2 Game State Validation Errors

**Impossible State Detection:**

* **Negative HP** – Should never occur (clamped to 0)
  * Mitigation: All damage resolution clamps HP to [0, max_hp]
  
* **Negative spell slots** – Should never occur
  * Mitigation: Validate spell slots available before casting
  
* **Dead entity acting** – Only living entities can take turns
  * Mitigation: Filter initiative to only living entities
  
* **Entity in two states simultaneously** – Player both in exploration and encounter
  * Mitigation: Single `game_mode` field enforces state exclusivity

**Invalid State Transitions:**

* **Move to non-existent room** – Action references unknown room_id
  * Response: "That room doesn't exist."
  * Logging: Log invalid room reference and retry parsing
  
* **Attack non-existent entity** – Target doesn't exist in encounter
  * Response: "That target isn't here."
  * Mitigation: Validate target_id against EncounterState.entities
  
* **Rest in combat** – Player tries to rest during encounter
  * Response: "You can't rest during combat."
  * Validation: Check `game_mode == exploration` before allowing rest

---

### 28.3 Data Corruption and Loading Errors

**Malformed JSON Files:**

* **Invalid JSON syntax** – Dungeon, spell, or encounter file contains syntax errors
  * Mitigation: Validate all JSON on game startup; fail with clear error message
  * Error Message: "Error loading dungeons.json: [parse error details]"
  
* **Missing required fields** – Spell missing `id` or `damage` field
  * Mitigation: Schema validation on load
  * Error Message: "Spell [name] is missing required field: damage"
  
* **Invalid enum values** – Attack has `type: "invalid_type"` not in [melee, ranged, magical]
  * Mitigation: Validate against allowed enums
  * Error Message: "Attack [id] has invalid type: [given]. Expected one of: melee, ranged, magical"

**Missing Data References:**

* **Encounter references non-existent enemy** – `encounter_001` includes `goblin_mage` but no such enemy template exists
  * Mitigation: Pre-validate all encounter definitions
  * Error Message: "Encounter goblin_casters references unknown enemy: goblin_mage"
  
* **Dungeon references non-existent room** – Room A connects to room Z but room Z doesn't exist
  * Mitigation: Validate all connections on dungeon load
  * Error Message: "Dungeon dungeon_01: room_hall references unknown connected room: room_phantom"
  
* **Spell references undefined status effect** – Spell applies `burning_intensely` which doesn't exist in status effect definitions
  * Mitigation: Cross-reference all status effects on load
  * Error Message: "Spell fire_blast applies unknown status effect: burning_intensely"

---

### 28.4 Recovery and Logging

**Graceful Degradation:**

* Invalid encounters are skipped (room becomes non-encounter)
* Invalid spells are removed from known_spells lists
* Invalid rooms are unreachable but don't crash the game

**Error Logging:**

All errors are logged with:

* Timestamp
* Error type and category
* Affected entity/action/state
* Stack trace (if applicable)
* Suggested recovery action

**Example Log Entry:**

```
[2026-02-04 14:32:15] ERROR | Data Validation
  Event: Dungeon load failed
  File: data/dungeons.json
  Issue: Room room_boss_lair references unknown connection: room_secret_exit
  Action: Skipping invalid connection; room is now a dead-end
  Severity: Non-fatal; game continues
```

---

### 28.5 Validation Checklist (Pre-Game)

Before allowing game start, verify:

- [ ] All dungeon JSON files parse successfully
- [ ] All encounter references valid enemies
- [ ] All room connections are bidirectional and valid
- [ ] All spells reference known status effects
- [ ] All attacks have valid damage dice strings (e.g., "1d6", "2d8+1")
- [ ] All entities have required fields (hp, ac, attack_modifier, etc.)
- [ ] Dungeon has valid entry_node and exit_node
- [ ] At least one encounter exists in the dungeon

If any validation fails, the game displays detailed error messages and does not start.

---

## 29. Replay and Session Logging

This section defines how gameplay sessions are logged and serialized for post-game analysis, replay, and transparency.

---

### 29.1 Purpose and Benefits

**Replay Logging** provides:

* **Transparency** – Players can review the entire combat sequence, including AI reasoning
* **Debugging** – Developers can inspect game state at any point to diagnose bugs
* **Analysis** – Understand player behavior, encounter difficulty, and balance
* **Reproducibility** – Re-run sessions with identical dice rolls to verify outcomes

---

### 29.2 Session Log Structure

Each game session produces a single JSON file: `session_YYYYMMDD_HHMMSS.json`

**Top-Level Schema:**

```json
{
  "session_id": "session_20260204_143215",
  "timestamp_start": "2026-02-04T14:32:15Z",
  "timestamp_end": "2026-02-04T14:45:30Z",
  "dungeon_id": "crypt_of_whispers",
  "result": "GAME_COMPLETE",
  "final_rewards": 250,
  "encounters_cleared": 3,
  
  "party": [
    {
      "entity_id": "player_1",
      "name": "Arin",
      "race": "Elf",
      "class": "Wizard",
      "final_hp": 12,
      "final_max_hp": 18
    }
  ],
  
  "events": [
    // See 29.3 below
  ]
}
```

**Fields:**

* **session_id** – Unique session identifier
* **timestamp_start/end** – UTC timestamps for session duration
* **dungeon_id** – Which dungeon was played
* **result** – Either `GAME_COMPLETE`, `GAME_OVER`, or `ABANDONED`
* **final_rewards** – Total points/coins earned
* **encounters_cleared** – Number of encounters defeated
* **party** – Final state of all players
* **events** – Append-only log of all game events

---

### 29.3 Event Log Schema

Every action, resolution, and state change is logged as an event.

**Generic Event Structure:**

```json
{
  "event_type": "action_resolved | combat_started | entity_died | rest_completed | ...",
  "round": 1,
  "timestamp": "2026-02-04T14:32:45Z",
  "actor_id": "player_1",
  "details": {}
}
```

---

### 29.4 Event Types and Details

#### action_initiated

Logged when a player input is received and parsed.

```json
{
  "event_type": "action_initiated",
  "timestamp": "2026-02-04T14:32:45Z",
  "actor_id": "player_1",
  "raw_input": "Cast fire bolt on the skeleton",
  "parsed_intent": "cast_spell",
  "confidence": 0.98,
  "details": {
    "action_type": "cast_spell",
    "target_id": "enemy_1",
    "spell_id": "fire_bolt"
  }
}
```

#### combat_started

Logged when an encounter begins.

```json
{
  "event_type": "combat_started",
  "timestamp": "2026-02-04T14:33:00Z",
  "round": 0,
  "encounter_id": "goblin_patrol",
  "room_id": "room_2",
  "details": {
    "initiative_order": ["player_1", "enemy_1", "enemy_2"],
    "entities": [
      {
        "entity_id": "player_1",
        "name": "Arin",
        "type": "player",
        "hp": 18,
        "ac": 12
      },
      {
        "entity_id": "enemy_1",
        "name": "Goblin Fighter",
        "type": "enemy",
        "hp": 8,
        "ac": 11
      }
    ]
  }
}
```

#### action_resolved

Logged when an action is executed and resolved.

```json
{
  "event_type": "action_resolved",
  "round": 1,
  "timestamp": "2026-02-04T14:33:05Z",
  "actor_id": "player_1",
  "action_type": "cast_spell",
  "details": {
    "spell_id": "fire_bolt",
    "target_id": "enemy_1",
    "roll_result": 18,
    "to_hit_dc": 12,
    "hit": true,
    "damage_rolled": "6",
    "damage_applied": 6,
    "narration": "Arin hurls a bolt of fire at the Goblin Fighter.\nThe spell strikes true, dealing 6 fire damage."
  }
}
```

#### status_effect_applied

Logged when a status effect is applied to an entity.

```json
{
  "event_type": "status_effect_applied",
  "round": 1,
  "timestamp": "2026-02-04T14:33:15Z",
  "entity_id": "player_1",
  "details": {
    "effect_type": "poisoned",
    "duration": 2,
    "magnitude": 2,
    "source": "enemy_1",
    "source_action": "poison_cloud"
  }
}
```

#### status_effect_triggered

Logged when a status effect triggers (e.g., poisoned damage at start of turn).

```json
{
  "event_type": "status_effect_triggered",
  "round": 2,
  "timestamp": "2026-02-04T14:33:30Z",
  "entity_id": "player_1",
  "details": {
    "effect_type": "poisoned",
    "damage_applied": 2,
    "duration_remaining": 1
  }
}
```

#### entity_died

Logged when an entity's HP reaches 0.

```json
{
  "event_type": "entity_died",
  "round": 3,
  "timestamp": "2026-02-04T14:33:45Z",
  "entity_id": "enemy_1",
  "details": {
    "name": "Goblin Fighter",
    "final_hp": 0,
    "killed_by": "player_1",
    "last_action": "attack"
  }
}
```

#### encounter_ended

Logged when an encounter concludes (all enemies defeated or all players dead).

```json
{
  "event_type": "encounter_ended",
  "round": 3,
  "timestamp": "2026-02-04T14:33:50Z",
  "encounter_id": "goblin_patrol",
  "details": {
    "result": "victory",
    "enemies_defeated": 2,
    "reward": 50,
    "player_final_states": [
      {
        "entity_id": "player_1",
        "name": "Arin",
        "final_hp": 12,
        "final_max_hp": 18,
        "status_effects": ["poisoned"]
      }
    ]
  }
}
```

#### exploration_moved

Logged when the party moves to a new room.

```json
{
  "event_type": "exploration_moved",
  "timestamp": "2026-02-04T14:34:00Z",
  "details": {
    "from_room": "room_1",
    "to_room": "room_2",
    "room_description": "A narrow hallway with mossy walls."
  }
}
```

#### rest_completed

Logged when the party completes a rest.

```json
{
  "event_type": "rest_completed",
  "timestamp": "2026-02-04T14:35:00Z",
  "details": {
    "rest_type": "short",
    "room_id": "room_3",
    "player_states_after": [
      {
        "entity_id": "player_1",
        "hp_before": 10,
        "hp_after": 14,
        "spell_slots_before": 1,
        "spell_slots_after": 2
      }
    ]
  }
}
```

#### game_ended

Logged when the game concludes.

```json
{
  "event_type": "game_ended",
  "timestamp": "2026-02-04T14:45:30Z",
  "details": {
    "result": "GAME_COMPLETE",
    "total_rewards": 250,
    "total_encounters": 3,
    "duration_seconds": 795,
    "final_party_state": [
      {
        "entity_id": "player_1",
        "name": "Arin",
        "final_hp": 12,
        "final_max_hp": 18
      }
    ]
  }
}
```

---

### 29.5 Log File Storage

**Directory Structure:**

```
GameMasterAI/
├── logs/
│   ├── sessions/
│   │   ├── session_20260204_143215.json
│   │   ├── session_20260204_150030.json
│   │   └── ...
│   └── errors/
│       ├── error_20260204_143500.json
│       └── ...
```

**File Naming Convention:**

* Sessions: `session_YYYYMMDD_HHMMSS.json`
* Errors: `error_YYYYMMDD_HHMMSS.json`

---

### 29.6 Accessing and Replaying Logs

**Viewing Recent Sessions:**

```
python main.py --view-logs [--limit 10]
```

**Analyzing a Specific Session:**

```
python main.py --analyze logs/sessions/session_20260204_143215.json
```

**Replaying a Session (Deterministic):**

```
python main.py --replay logs/sessions/session_20260204_143215.json
```

When replaying, all dice rolls are taken from the log, ensuring identical outcomes.

---

### 29.7 Log Privacy and Cleanup

* **Retention**: Sessions are kept indefinitely (up to disk space)
* **Privacy**: Logs contain no personal information beyond usernames
* **Manual Cleanup**: Use `python main.py --cleanup-logs --older-than 30d` to remove old logs

---

## 29. Out of Scope

* Grid-based movement
* Advanced RPG mechanics
* Multiplayer networking
* Persistent character progression

---

## 16. Engine Pseudocode

This section provides high-level pseudocode describing how the game engine operates. It is intended to guide implementation and demonstrate the control flow of the AI agent and game states.

---

### 16.1 Main Game Loop

```
initialize GlobalGameState
load dungeon data
set current_room to dungeon.entry_node
set game_mode to exploration

while game not over:
    get player_input

    if game_mode == exploration:
        handle_exploration(player_input)

    else if game_mode == encounter:
        handle_encounter(player_input)
```

---

### 16.2 Exploration Loop

```
function handle_exploration(input):
    intent = parse_intent(input)
    action = map_intent_to_action(intent)

    if not validate_action(action, GlobalGameState):
        narrate_invalid_action()
        return

    if action.type == move:
        update current_room
        mark room as visited

        if room has unresolved encounter:
        narrate encounter presence
        prompt party of engagement
        
        create EncounterState
        roll initiative
        set game_mode to encounter
        narrate encounter start

    else if action.type == explore:
      if room first visit:
        narrate room description
      else:
        narrate brief reminder or details on request

    else if action.type == rest:
        apply rest rules
        update player stats
        narrate rest outcome
```

---

### 16.3 Encounter Loop

```
function handle_encounter(input):
    current_entity = EncounterState.active_entity

    if current_entity is enemy:
        action = enemy_ai_decision(current_entity)
    else:
        intent = parse_intent(input)
        action = map_intent_to_action(intent)

    if not validate_action(action, EncounterState):
        narrate_invalid_action()
        return

    resolve_action(action, EncounterState)
    append to combat_log

    if victory condition met:
        sync entity data back to GlobalGameState
        mark encounter as cleared
        destroy EncounterState
        set game_mode to exploration
        narrate victory
        return

    advance_turn()
```

---

### 16.4 Turn Resolution

```
function advance_turn():
    apply end-of-turn effects
    move to next entity in initiative_order

    if initiative cycle complete:
        increment round
```

---

### 16.5 Status Effect Resolution

```
function resolve_status_effects(entity):
    for each status in entity.status_effects:
        if status triggers at start of turn:
            apply effect
            decrement duration

        if duration <= 0:
            remove status
```

---

### 16.6 Design Notes

* The engine is deterministic; randomness is limited to dice rolls
* The AI agent never bypasses validation or rules
* State transitions are explicit and predictable
* Exploration and encounter logic are fully separated

This pseudocode completes the system-level design and serves as a direct blueprint for implementation.

---

## 17. Implementation Plan and File Structure

This section outlines a realistic implementation plan and a modular file structure suitable for a 2–3 week solo project. The goal is to minimize complexity while maintaining clean separation of concerns.

---

### 17.1 Recommended Tech Stack

* **Language**: Python 3
* **UI**: Terminal (CLI) or simple web UI (optional)
* **Data Format**: JSON (for dungeon, encounters, spells)
* **Optional NLP**: Rule-based intent parsing or lightweight LLM API

---

### 17.2 Project File Structure

```
GameMasterAI/
│
├── main.py                 # Entry point, main game loop
│
├── engine/
│   ├── __init__.py
│   ├── game_engine.py      # State switching, main handlers
│   ├── exploration.py      # Exploration logic
│   ├── encounter.py        # Combat logic
│   ├── validation.py       # Action validation rules
│   └── resolution.py       # Damage, spells, status effects
│
├── agent/
│   ├── __init__.py
│   ├── parser.py           # Intent parsing (NLP)
│   ├── action_mapper.py    # Intent → Action object
│   └── enemy_ai.py         # Simple enemy decision logic
│
├── models/
│   ├── __init__.py
│   ├── entities.py         # Player / Enemy classes
│   ├── states.py           # GlobalGameState, EncounterState
│   └── actions.py          # Action object definitions
│
├── data/
│   ├── dungeons.json       # Prefabricated dungeon layout
│   ├── encounters.json     # Enemy groups per room
│   ├── spells.json         # Spell definitions
│   └── attacks.json        # Attack definitions
│
├── utils/
│   ├── dice.py             # Dice rolling utilities
│   └── narration.py        # Text outsput helpers│
└── README.md               # How to run and demo 

```

---

### 17.3 Implementation Timeline (2–3 Weeks)

#### Week 1: Core Engine & Data

* Implement state models (GlobalGameState, EncounterState)
* Load dungeon, encounter, spell, and attack data
* Implement exploration movement and encounter triggering

#### Week 2: Combat & Agent Logic

* Implement turn system and initiative
* Implement attacks, spells, and status effects
* Implement action validation and resolution
* Implement basic enemy AI

#### Week 3: Polish & Demo Prep

* Add narration and logging
* Improve intent parsing robustness
* Add simple UI improvements
* Testing and bug fixes
* Prepare demo scenario

---

### 17.4 Scope Control Guidelines

To stay within time limits:

* Prefer rule-based intent parsing over complex NLP
* Use prefabricated dungeon and encounters
* Keep enemy AI simple and deterministic
* Avoid adding new mechanics after Week 2

This implementation plan ensures the project remains achievable while fully demonstrating AI agent principles.

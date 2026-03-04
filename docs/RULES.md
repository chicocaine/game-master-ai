# Game Rules

> This document is the canonical gameplay source of truth.
> When gameplay statements conflict with `docs/DOCUMENTATION.md`, update `docs/DOCUMENTATION.md` to match this file.

## 1) Core Concepts
- Deterministic engine rules are authoritative for state mutation; LLM outputs are interpreted intents and narration only.
- Rules precedence when conflicts appear: validation constraints > resolution rules > narration text.
- Dice checks use d20 for hit/saving/initiative flows and dice notation for damage/healing values.
- `ABANDON`, `QUERY`, and `CONVERSE` are legal in every game state.

### 1.1) Canonical Naming
- Action schema names follow `docs/ACTIONS.md`.
- Use `target_instance_ids` for encounter target parameters.
- Use `race`, `archetype`, and `weapons` for `create_player` parameters.
- Use `spell_slots` as canonical spell resource terminology.
- `MANA_UPDATED` / `mana_updated` is retained as a legacy event label for compatibility.

## 2) Character Creation
- Character creation is emitted as `create_player` with parameters including `name`, `description`, `race`, `archetype`, and `weapons`.
- `name` and `description` may be generated from player intent, but all structural fields must pass validation.
- Stats are derived from race base values plus archetype modifiers.
- Attacks, spells, immunities, resistances, and vulnerabilities are merged from race, archetype, weapon(s), and own known lists.
- Archetype must satisfy race `archetype_constraints`; equipped weapons must satisfy archetype `weapon_constraints`.
- Successful creation adds a new player instance with a unique `player_instance_id` to the party.
- `remove_player` removes the selected player instance from the party.

## 3) Session Flow
- `PRE_GAME` → `EXPLORATION` → `ENCOUNTER` (as needed) → `POST_GAME`.
- `start` is valid only when at least one party member exists and a dungeon is selected.
- `finish` resets the game back to `PRE_GAME`.
- Action parser `clarify` responses do not advance turn or phase.


## 4) Exploration
- Legal actions in `EXPLORATION`: `move`, `explore`, `rest`, `converse`, `query`, `abandon`.
- `move` requires both: (1) destination room is connected, and (2) current room is cleared.
- Entering a room with active uncleared encounter transitions to `ENCOUNTER`.
- Reaching and clearing the dungeon end room transitions to `POST_GAME`.
- `explore` reveals room details and emits exploration events.

## 5) Social & Interaction
- `QUERY` is out-of-character information retrieval and must remain context-grounded.
- `CONVERSE` is in-world dialogue and must not directly mutate game state.
- Any state-changing result implied by dialogue must be converted into a legal action and resolved by the engine.

## 6) Combat
- Legal actions in `ENCOUNTER`: `attack`, `cast_spell`, `end_turn`, `converse`, `query`, `abandon`.
- Initiative is rolled once at encounter start for all combatants; turn order is descending initiative.
- Player turns use parser output + validation; enemy turns use enemy-AI output + validation, then fallback action when needed.
- Attack resolution: hit check (`d20 + modifiers` vs AC, or save-vs-DC where defined), then damage with multipliers, then state events (`ATTACK_HIT`/`ATTACK_MISSED`, `DAMAGE_APPLIED`, `HP_UPDATED`, `DEATH`).
- Multipliers: 
    - `immunity`: 0x
    - `resistance`: 0.5x
    - `vulnerability`: 2x
- Encounter ends when all enemies are defeated (return to `EXPLORATION`) or all players are defeated (transition to `POST_GAME` defeat).
### 6.1) Control Types
- `stunned` - skips the turn
- `asleep` - skips the turn
- `silenced` - cannot cast spell (cast_spell condition: `actor` is not `silenced`)
- `restrained` - cannot attack (attack condition: `actor` is not `restrained`)

## 7) Resting & Recovery
- Rest is valid only where requested `rest_type` is allowed by room `allowed_rests`.
- A room can only be rested once (`is_rested = True` prevents repeated rest in the same room).
- Short rest restores partial HP and partial spell slots.
- Long rest restores full HP and full spell slots.
- Only long rest may revive a downed entity (`hp == 0`); short rest cannot revive.

## 8) Magic & Special Abilities
- Spell casting is legal only on the caster's turn and only if spell resource cost is payable from current spell slots.
- If spell DC is 0, the spell resolves automatically; otherwise targets make saving throws vs spell DC.
- AOE spells resolve per target in `target_instance_ids`.
- Heal spells skip hit-roll logic and apply healing directly through resolution rules.

## 9) Status Effects & Conditions
- Status effect durations tick down by 1 at the end of each actor turn; effects reaching 0 are removed and emit `STATUS_EFFECT_REMOVED`.
- DoT and HoT effects resolve every turn according to their effect definition.
- Control effects are checked at relevant turn gates (typically start-of-turn).
- AC modifier effects apply AC changes on application and revert when the effect ends.
- Resistance, immunity, and vulnerability interactions are applied during damage resolution.
- Non-stackable status-effect types keep the stronger/longer-effective instance; DoT/HoT may stack by rule definition.
- AC and ATK modifier spells follow an overwrite rule, only one of status effect type `ATKMOD` or `ACMOD` can be active for a single entity at a time. 

## 10) Inventory, Gear & Resources
- Equipped weapons gate available attack/spell options and must satisfy archetype constraints.
- Resource spending (spell slots and consumables when implemented) is validated before action resolution.
- Loot and rewards are represented as deterministic state updates and events, not narration-only outcomes.

## 11) Progression
- Progression is currently dungeon-structure driven rather than XP-leveling.
- Room/encounter `clear_reward` values are accumulated for post-game summary.
- Additional progression systems can be layered without changing core action-validation contracts.

## 12) Death, Failure & Consequences
- Entities at 0 HP are defeated/downed per encounter rules.
- Party defeat in encounter transitions run outcome to post-game defeat flow.
- Revival through rest is limited: long rest only, and only when rest is otherwise legal.
- Failures from invalid actions emit rejection/error events and do not mutate state.

## 13) Dungeon & Encounter Generation
- A selected dungeon defines rooms, room graph connectivity, encounters, and end-room completion target.
- Encounter composition is deterministic from dungeon data for a given run setup.
- Entering an uncleared encounter room triggers encounter state and initiative setup.
- Clear rewards and completion flags are carried into post-game results.

## 14) AI/GM Adjudication Guidelines
- Ambiguous player intent must return `clarify` with explicit options, not guessed targets.
- Invalid or malformed actions are rejected safely; the engine requests correction.
- Parser JSON failures emit error events and re-prompt the same actor without advancing turn order.
- LLMs may interpret intent and generate narration but cannot directly apply state changes.

## 15) Logging, Events & Persistence
- Every resolved action emits structured events as the authoritative turn audit trail.
- Narration is derived from event streams and is not the source of truth for state.
- Validation rejections and parser failures are logged as explicit events.
- Session summaries include outcomes such as rooms cleared, enemies defeated, and resource impact.

## 16) Optional / Variant Rules
- Optional modes may alter difficulty, recovery strictness, and enemy behavior profiles.
- Variants must preserve action schema contracts and deterministic validation/resolution boundaries.
- Any enabled variant should be declared at run start and logged in session metadata.

# GameMasterAI: An LLM-Based Natural Language Agent for Rule-Constrained Interactive Game Management

## Abstract
GameMasterAI is a rule-guided natural language processing (NLP) agent designed to manage a text-based, turn-based tabletop dungeon crawler game. It addresses the challenge of enabling natural language interaction within a rule-constrained, deterministic game environment. Traditional text-based games rely on fixed command inputs, limiting flexibility and immersion. Meanwhile, large language models (LLMs) excel at interpreting natural language but often struggle to enforce strict logical rules. This project bridges that gap by designing an LLM-based AI agent that manages a turn-based dungeon game while strictly adhering to predefined mechanics.
We developed a node-based, text-driven dungeon system where players interact using free-form language. The LLM interprets intent, maps commands into structured action objects, validates them against a deterministic rule engine, and narrates outcomes. Combat, status effects, initiative order, and state transitions are handled through explicit schemas and validation layers to ensure consistency and explainability.
The system leverages OpenAI’s GPT models via API integration, structured JSON state representations, and a modular Python engine. The expected contribution is a working prototype demonstrating how LLMs can operate as controlled agents within rule-bound environments—balancing generative flexibility with deterministic logic. This work highlights the feasibility of combining natural language understanding with formal state management for interactive AI-driven systems.
## Keywords
Large Language Models (LLMs), Agentic AI, Prompt Engineering, Rule-Based Systems, Structured Output Generation, Turn-Based Game Systems, State Machine Architecture
## 1 Introduction
### 1.1 Background
Interactive digital games traditionally rely on structured inputs such as buttons or predefined commands. However, natural language interfaces offer an immersive and flexible interaction. Early work in natural language understanding (NLU) and dialogue systems aimed to interpret human intent computationally [1]. With the emergence of transformer-based architectures such as those introduced by Vaswani et al. [2], language models have significantly improved in contextual understanding.
Large Language Models (LLMs) such as GPT-3 and GPT-4 demonstrate strong reasoning and language generation capabilities [3]. However, these models are probabilistic and may produce outputs that violate strict logical rules. Research in AI agents emphasizes the importance of separating decision-making from environment execution to ensure reliable behavior [4].
In interactive game management, maintaining state consistency is critical. If a model directly controls game logic without constraints, it may produce inconsistent or invalid actions. Therefore, combining LLM-based intent recognition with a deterministic rule engine becomes necessary.
### 1.2 Problem Context
The core challenge is balancing flexible natural language input with strict rule enforcement and deterministic state transitions. LLMs are effective at interpreting ambiguous natural language and generating immersive narration while providing contextual reasoning. Instead of replacing game logic, the LLM in GameMasterAI functions as an interpreter and narrator, while a structured engine enforces rules.
### 1.3 Overview of the System
GameMasterAI is structured as a hybrid pipeline that chains natural language processing with deterministic game logic. Players interact using free-form text; a dedicated LLM component interprets that input and emits a structured `Action` object. The action is then validated and resolved by a rule-governed engine that is entirely independent of the language model. The engine produces an `Event` stream—an ordered log of everything that occurred during the turn—which a second LLM role converts into immersive narrative prose before the output is delivered to the player.

The system operates as a finite state machine with four states: **PRE_GAME** (party assembly and dungeon selection), **EXPLORATION** (room traversal, resting, and conversation), **ENCOUNTER** (turn-based combat), and **POST_GAME** (results and session close). Legal transitions between states are enforced at action validation time so that no action resolver is invoked in a state where it is not permitted.

The LLM is assigned four clearly separated, read-only roles:
- **Action Parser** — maps natural language to a structured `Action` JSON or issues a `Clarify` request when context is ambiguous.
- **Query/Conversation Responder** — answers player questions and drives in-world dialogue without modifying state.
- **Narration Generator** — translates the event stream for a turn into second-person narrative prose.
- **Enemy AI** — selects enemy actions each combat turn by reasoning over an encounter summary.

All four roles receive a structured game-state summary as context but are prohibited from writing to that state directly. This constraint guarantees that the game remains fully reproducible and auditable: replaying the same event log always yields the same game state, regardless of which language model produced the events.
### 1.4 Importance of the Study
This study demonstrates how LLMs can function as bounded agents rather than uncontrolled generators. It contributes to understanding hybrid AI systems that combine probabilistic reasoning with rule-based engines. The architecture reflects real-world AI systems where language interfaces control structured environments such as AI copilots, workflow automation agents, intelligent tutoring systems, etc.
### 1.5 Objectives
#### 1.5.1 General Objective
To design and implement a rule-constrained AI agent that interprets natural language commands and manages a deterministic, turn-based dungeon crawler game using structured state control.
#### 1.5.2 Specific Objectives
1. To separate deterministic game logic from probabilistic language model inference by introducing a validation engine that rejects ill-formed or illegal actions before they reach the resolution layer.
2. To implement a multi-role LLM architecture in which the action parser, conversation responder, narration generator, and enemy AI are served by independently configurable system prompts and model parameters.
3. To design and enforce typed data models for all game entities—`Race`, `Archetype`, `Weapon`, `Entity`, `Player`, `Enemy`, `Dungeon`, `Action`, `Event`, and `Narration`—validated against JSON Schema at load time.
4. To develop an action parser capable of handling ambiguous natural language through a structured `Clarify` response that re-prompts the player without advancing the game turn.
5. To implement a context budget management system that assembles prioritised game-state sections for each LLM call and truncates lower-priority content when the token budget is exceeded.
6. To evaluate system correctness through deterministic unit tests and LLM accuracy through a golden-dataset harness measuring `action_type_accuracy`, `parse_success_rate`, and `validation_pass_rate`, with a secondary quality layer assessing coherence, relevance, and hallucination rate.
## 2 Methodology
### 2.1 System Design
GameMasterAI follows a **hybrid agent architecture** in which probabilistic language model inference is strictly confined to interpretation and generation, while all state mutations are delegated to a deterministic engine. This design is motivated by the observation that allowing an LLM to write game state directly—even with careful prompting—introduces consistency risks that compound over a session. By treating the LLM as a read-only reasoner and the engine as the sole writer, the system achieves both the conversational flexibility of a language model and the correctness guarantees of a rule-based program.

The design is organised around three invariants:
1. **No LLM call may mutate game state.** Every state change passes through the validation and resolution engine.
2. **Every game-relevant occurrence is recorded as an `Event`.** The event log is the single source of truth for a session and is sufficient to reconstruct any game state.
3. **Each LLM role receives only the context it requires.** The action parser does not receive conversation history; the narration generator does not receive raw player input. This minimises context pollution and keeps token budgets predictable.

### 2.2 System Architecture
The system is organised into six layers:

| Layer | Modules | Responsibility |
|-------|---------|---------------|
| **Data** | `data/`, `registry/` | Static JSON game definitions; in-memory indexed registries |
| **Models** | `models/` | Typed dataclass representations of all game entities |
| **Core** | `core/` | Deterministic game logic: `actions.py`, `validation.py`, `rules.py`, `resolution/`, enums/events/narration, and dice |
| **Engine** | `engine/` | Runtime infrastructure: `game_loop.py`, `state_manager.py`, low-level `llm_client.py`, and orchestration |
| **Agent** | `agent/` | Decision layer: `agent_manager.py`, `player_parser.py`, `narrator.py`, `enemy_ai.py`, `context_builder.py`, and `memory.py` |
| **Utilities** | `util/` | JSON Schema validator, entity factory, logging |

Data flows through the system in a strict one-way pipeline: player input enters the agent layer, is validated and resolved by the engine layer, and surfaces to the player again only as narrated output. No component below the agent layer initiates an LLM call.

### 2.3 Tools and Technology

| Component | Technology |
|-----------|----------|
| Implementation language | Python 3.11 |
| LLM provider | OpenAI API (GPT-4o, GPT-4o-mini) |
| Data serialisation | JSON with JSON Schema validation (`jsonschema`) |
| Testing framework | `pytest` |
| Logging | Python `logging` module with structured JSONL output |
| Dependency management | `pip` with `requirements.txt` |

The LLM client (`engine/llm_client.py`) is a thin wrapper around the OpenAI SDK that handles retries with exponential backoff, records request metadata for performance evaluation, and raises typed exceptions (`LLMParseError`, `LLMTimeoutError`) for explicit failure-mode handling by callers.

### 2.4 Data Sources
Unlike RAG systems [5], GameMasterAI does not retrieve data from external documents. Instead, the game state is injected directly into the LLM context and acts as structured grounding information.
### 2.5 Prompt Engineering Strategy
Each LLM role is served by a dedicated system prompt template stored under `agent/prompts/`. The prompt design follows four principles:

1. **Schema anchoring.** The action parser prompt contains the complete `Action` JSON schema and a table of every legal `ActionType` with its required parameters. The narration prompt embeds the `Event` type vocabulary. This constrains output shape without relying solely on the model's generalisation.
2. **Few-shot grounding.** The action parser includes labelled examples mapping canonical player phrases to the expected `Action` output. This reduces format errors for structurally complex or ambiguous inputs.
3. **Chain-of-thought logging.** Every action parser call requires a `reasoning` field in the response. This field is logged for debugging but is never shown to the player. It improves parse quality on complex inputs by encouraging the model to reason before committing to structured output.
4. **Explicit fallback contract.** The action parser prompt specifies that any input that cannot be mapped to a legal `ActionType` must be returned as `{"type": "query", "parameters": {"question": "<original input>"}}`. This prevents silent failure modes where the model omits output or produces an unrecognised type.

When the action parser cannot unambiguously resolve a required parameter—most commonly `target_instance_ids` when multiple enemies share the same name—it returns a `Clarify` object rather than guessing. The engine delivers the clarification question to the player without advancing the turn.

### 2.6 Memory Handling
LLM calls in GameMasterAI are categorised by statefulness:

- **Stateless (fresh context per call):** Action parser, narration generator, and enemy AI. Each call receives a fully assembled system prompt and a single user message. No prior turn messages are included. This keeps token usage predictable and prevents context drift across turns.
- **Stateful (rolling window):** Query and conversation responder. A conversation history of the last N player messages and GM replies is maintained in the OpenAI `messages[]` chat format. Only `role: user` and `role: assistant` entries from the conversation role are included; the system prompt is re-injected fresh on every call with the current game state. The window size N is configurable (default 10) and is the first section dropped when the context budget is exceeded.

### 2.7 Model Configuration
Model selection and generation parameters are configured per LLM role to balance cost, latency, and output quality:

| Role | Recommended Model | Temperature | Rationale |
|------|-------------------|-------------|----------|
| Action Parser | `gpt-4o-mini` | 0.0 | Deterministic structured output; JSON correctness prioritised over variety |
| Conversation Responder | `gpt-4o` | 0.7 | Dialogue quality and NPC persona depth justify a higher-capability model |
| Narration Generator | `gpt-4o` | 0.7 | Narrative variety is desirable; streaming enabled for time-to-first-token |
| Enemy AI | `gpt-4o-mini` | 0.3 | Structured output; slight variance improves enemy behaviour diversity |

A `max_tokens` ceiling is set per role to cap completion length. The `ContextBuilder` enforces a `max_context_tokens` budget during context assembly, dropping lower-priority sections (history, world lore) first when over budget.

### 2.8 Testing Procedures
System quality is verified through three complementary testing layers:

**Functional unit tests** (`tests/`, `pytest`) cover all deterministic components with no LLM calls: data model construction and constraint validation, `Action` and `Event` construction and serialisation, registry loading and ID resolution. Planned additions include combat resolution with seeded RNG, state machine transitions, exploration resolution, entity constraint enforcement, and dice notation parsing.

**LLM accuracy evaluation** is performed offline against a static golden dataset (`tests/eval/golden_actions.jsonl`). Each record pairs a `raw_input` string and a game-state context with expected `action_type` and `parameters`. The eval runner (`tests/eval/run_eval.py`) calls the action parser and computes accuracy metrics against ground truth. A CI threshold gate requires `action_type_accuracy >= 0.90` and `parse_success_rate >= 0.98`.

**Quality evaluation** uses a secondary judge LLM (or human review) to score narration output for coherence, relevance, and tone consistency. Hallucination detection cross-checks numeric and entity claims in LLM output against the context payload that was supplied, targeting a hallucination rate below 0.05.

### 2.9 Evaluation Metrics

| Category | Metric | Definition |
|----------|--------|----------|
| **Action Parsing** | `action_type_accuracy` | % of cases where `action.type` matches expected |
| | `parameter_exact_match` | % of cases where all expected parameters match exactly |
| | `parse_success_rate` | % of LLM responses producing valid, parseable JSON |
| | `validation_pass_rate` | % of parsed actions passing `validate_action()` without errors |
| **Narration** | Coherence (1–5) | Grammatically correct prose that follows logically from events |
| | Relevance (1–5) | All events addressed; no fabricated events in output |
| | Tone consistency | Sentiment of narration matches event severity |
| **Hallucination** | `hallucination_rate` | Hallucinated verifiable claims / total verifiable claims; target < 0.05 |
| **Performance** | P50 / P95 latency | Per-role wall-clock response time (Action Parser < 1.5 s P50; Narration < 2.5 s P50) |
| **Cost** | Token cost per session | Total USD cost computed from prompt + completion tokens per role |

### 2.10 Design Rationale
The key design decision was to restrict the LLM to interpretation and narration roles. Allowing direct state manipulation by a probabilistic model risks inconsistency. By separating reasoning from execution, the system maintains both flexibility and correctness.
This hybrid approach demonstrates how LLMs can function as bounded agents within structured environments, which is critical for reliable AI deployment in real-world applications.
## 3 System Design and Architecture
This section describes the structural design of GameMasterAI, including its architectural layers, data flow, component interactions, and design principles. The system is built using a modular, hybrid architecture that separates probabilistic natural language reasoning from deterministic game logic execution.
The key architectural goal is controlled autonomy: allowing the LLM to understand and narrate the game while ensuring that all rule enforcement remains deterministic and verifiable
### 3.1 Architectural Design Principles

GameMasterAI is built on four foundational design principles that govern every structural decision in the system.

**Separation of inference and execution.** The LLM is never permitted to write game state directly. Its outputs — `Action` JSON and narrative text — are artefacts that enter the deterministic side of the system as data, not as instructions that bypass validation. This boundary is enforced architecturally: LLM modules have no reference to mutable game state objects; they receive summaries and return structured responses.

**Event sourcing as the audit trail.** Every observable outcome within a session — a hit, a miss, a room entered, a spell cast, a status effect ticking — is recorded as an immutable `Event` object carrying a UUID, UTC timestamp, typed payload, and a `source` identifier. The event log is sufficient to reconstruct any game state at any point in a session, enabling deterministic session replay, regression testing, and transparent debugging without LLM re-invocation.

**Definition–instance separation.** Static game data (races, archetypes, weapons, spells, enemies, dungeons) are stored as *definition* objects identified by stable string IDs in JSON files under `data/`. At runtime, combatants are instantiated with separate `instance_id` values so the same definition can be used concurrently across sessions or multiple times within one session without ID collision. The event log references `instance_id` values exclusively, making every event unambiguous regardless of how many copies of a template are active.

**Context minimisation per LLM role.** Each LLM role receives only the context it requires to perform its function. The action parser does not receive conversation history. The narration generator does not receive raw player input. The enemy AI does not receive party conversation history. Keeping context payloads lean reduces token consumption, limits surface area for hallucination, and makes each role's prompt contract easier to specify and test.

### 3.2 System Architecture

The system is decomposed into six layers arranged in a strict dependency hierarchy. Lower layers are unaware of higher layers; data flows downward through the stack and results surface upward as events and narration.

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent Layer                         │
│  AgentManager · ContextBuilder · PlayerParser · Narrator    │
│  EnemyAI · Memory                                            │
├─────────────────────────────────────────────────────────────┤
│                        Engine Layer                         │
│  GameLoop · StateManager · LLMClient                        │
├─────────────────────────────────────────────────────────────┤
│                         Core Layer                          │
│  ActionType · EventType · Action · Event · Narration        │
│  ValidationEngine · ResolutionEngine · DiceEngine · Rules   │
├─────────────────────────────────────────────────────────────┤
│                        Models Layer                         │
│  Entity · Player · Enemy · Race · Archetype · Weapon        │
│  Spell · Attack · Dungeon · Room · Encounter · StatusEffect │
├─────────────────────────────────────────────────────────────┤
│                       Registry Layer                        │
│  RaceRegistry · ArchetypeRegistry · WeaponRegistry          │
│  SpellRegistry · AttackRegistry · EnemyRegistry             │
│  DungeonRegistry · StatusEffectRegistry                     │
├─────────────────────────────────────────────────────────────┤
│                         Data Layer                          │
│  data/*.json · data/schemata/*.schema.json                  │
└─────────────────────────────────────────────────────────────┘
```

The **Agent Layer** is the only layer permitted to make LLM API calls. It communicates with the Engine Layer through orchestration interfaces and returns structured artifacts (`Action`-like decisions, narration text). The **Engine Layer** runs the loop, state transitions, and external integrations; game-rule legality and deterministic action effects are delegated to the **Core Layer**. The **Core Layer** defines shared data contracts and deterministic rule engines. The **Registry Layer** loads and indexes the static Data Layer at application start and exposes read-only lookups by ID to the Models and Core/Engine layers.

### 3.3 Core Components

**`GameStateMachine` (`engine/`).**  
Maintains the current game state (`PRE_GAME`, `EXPLORATION`, `ENCOUNTER`, `POST_GAME`) and the full mutable game state object (party, current dungeon, current room, turn order, turn index). Exposes a single `submit_action(action) → List[Event]` interface that routes the validated action to the appropriate resolver and returns the resulting event list. State transitions are side effects of specific events (e.g., `ENCOUNTER_STARTED` transitions to `ENCOUNTER`; `ENCOUNTER_CLEARED` returns to `EXPLORATION`).

**`ValidationEngine` (`core/validation.py`).**  
Stateless component that checks a parsed `Action` against current game state and the `REQUIRED_PARAMETERS` table. Returns a list of error strings; an empty list means the action is legal. Checks include: correct `ActionType` for current state, presence and type of all required parameters, validity of referenced IDs (`target_instance_ids`, `attack_id`, `spell_id`, `room_id`) against the active registry and game state, and game-logic preconditions (target must be alive, room must be connected, etc.).

**`ResolutionEngine` / sub-resolvers (`core/resolution/`).**  
Separate resolver modules handle each game phase: `PreGameResolver` processes party management; `ExplorationResolver` handles movement, exploration, and rest; `CombatResolver` handles attack and spell resolution, initiative, and status effect ticks. The `DiceEngine` (`core/dice.py`) provides a seeded `roll(expression)` function accepting standard dice notation (`NdX`, `NdX+M`, `NdX-M`) so combat resolution is fully reproducible given a seed.

**`LLMClient` (`engine/llm_client.py`).**  
Sends OpenAI-format `system` + `user` message pairs. Implements exponential-backoff retry on rate-limit and transient errors. Records an `LLMResponseRecord` to `logs/llm_performance.jsonl` for every call, capturing model name, token counts, latency, role, and parse success. Raises `LLMParseError` or `LLMTimeoutError` on unrecoverable failure so callers can apply role-specific fallback logic.

**`ContextBuilder` (`agent/context_builder.py`).**  
Assembles the context payload for each LLM call from the current `GameState`. Sections are tagged with a priority integer; if the assembled payload exceeds `max_context_tokens`, sections are dropped from lowest priority first. Token size is estimated with a `len(text) / 4` character-count heuristic and reconciled against provider-reported counts after each call.

**`PlayerParser` (`agent/player_parser.py`).**  
Calls the LLM, parses the JSON response, and returns either a `ClarifyResponse` (which the engine delivers to the player without advancing the turn) or a fully validated `Action`. Operates at `temperature=0.0` for deterministic structured output.

**`Narrator` (`agent/narrator.py`).**  
Receives the complete event list for a turn and produces a `Narration` object containing immersive prose and a `tone` tag. Uses streaming (SSE) to minimise time-to-first-token. Events sharing the same logical beat are described in a single merged sentence.

**`Conversation handling` (`agent/agent_manager.py` + `agent/memory.py`).**  
Handles `QUERY` and `CONVERSE` actions with a stateful rolling history window. Bypasses deterministic resolution and returns grounded conversational output only.

**`EnemyAI` (`agent/enemy_ai.py`).**  
Called once per enemy turn in an `ENCOUNTER`. Returns an `Action` in the same schema as the player action parser. Falls back to `fallback_enemy_action` — attack targeting the lowest-HP player — if the LLM response fails to parse or fails validation.

**Registries (`registry/`).**  
One registry class per entity type. Each registry loads and validates its JSON file against the corresponding JSON Schema at construction time, then indexes all definitions by `id` in an in-memory dict. Exposes `get_by_id(id: str) → Model` and `list_all() → List[Model]`. Registries are instantiated once at application start and shared as read-only singletons.

### 3.4 Data Flow Architecture

A single turn of gameplay involves the following data flow:

```
  Player (natural language input)
           │
           ▼
  ┌─────────────────────┐
  │    ContextBuilder   │  ── assembles game state summary, party, room,
  │                     │     rules, history into a context dict
  └──────────┬──────────┘
             │ context dict
             ▼
  ┌─────────────────────┐
  │    ActionParser     │  ── LLM call (temperature=0.0)
  │                     │     returns Action JSON or Clarify JSON
  └──────────┬──────────┘
             │
    ┌────────┴────────┐
    │  type=clarify?  │── yes ──► deliver question to player, re-prompt (no turn advance)
    └────────┬────────┘
             │ no: Action object
             ▼
  ┌─────────────────────┐
  │  ValidationEngine   │  ── checks ActionType legality, required params,
  │                     │     ID validity, game-logic preconditions
  └──────────┬──────────┘
             │
    ┌────────┴────────┐
    │   errors?       │── yes ──► emit ACTION_REJECTED event, re-prompt
    └────────┬────────┘
             │ no: validated Action
             ▼
  ┌─────────────────────┐
  │  ResolutionEngine   │  ── deterministic: dice rolls, stat mutations,
  │  (phase resolver)   │     state transitions, status effect ticks
  └──────────┬──────────┘
             │ List[Event]
             ▼
  ┌─────────────────────┐
  │   GameStateMachine  │  ── applies events to mutable game state,
  │                     │     triggers state transitions
  └──────────┬──────────┘
             │ List[Event] (immutable, appended to session log)
             ▼
  ┌─────────────────────┐
  │  NarrationGenerator │  ── LLM call (temperature=0.7, streaming)
  │                     │     returns Narration (text + tone)
  └──────────┬──────────┘
             │
             ▼
  Player (narrative output + implicit game state delta)
```

Enemy turns follow the same pipeline, with the `EnemyAI` component substituting for the `ActionParser` and `ContextBuilder` using an encounter-specific payload instead of the full game state summary.

`QUERY` and `CONVERSE` actions are intercepted after the `ValidationEngine` and routed directly to the `ConversationResponder`, bypassing the `ResolutionEngine` and `NarrationGenerator` entirely.

### 3.5 Component Interaction Matrix

The table below indicates which source component initiates a call to each target component. A filled cell means the source reads from or calls the target; an empty cell means no direct dependency.

| Source \ Target | LLMClient | ContextBuilder | ValidationEngine | ResolutionEngine | GameState | Registries | EventLog |
|----------------|:---------:|:--------------:|:----------------:|:----------------:|:---------:|:----------:|:--------:|
| **ActionParser** | ✓ | ✓ | ✓ | | | | |
| **NarrationGenerator** | ✓ | ✓ | | | | | |
| **ConversationResponder** | ✓ | ✓ | | | | | |
| **EnemyAI** | ✓ | ✓ | ✓ | | | | |
| **GameStateMachine** | | | ✓ | ✓ | ✓ | | ✓ |
| **ValidationEngine** | | | | | ✓ | ✓ | |
| **ResolutionEngine** | | | | | ✓ | ✓ | ✓ |
| **ContextBuilder** | | | | | ✓ | ✓ | |
| **Registries** | | | | | | ✓ | |

Key observations:
- The **Agent Layer** components (ActionParser, NarrationGenerator, ConversationResponder, EnemyAI) interact only with the LLMClient, ContextBuilder, and ValidationEngine — they have no direct dependency on the ResolutionEngine or mutable GameState.
- The **ResolutionEngine** is the sole writer to GameState and EventLog; no agent component reaches past ValidationEngine to touch these.
- **Registries** are read-only leaf nodes consumed by ValidationEngine, ResolutionEngine, and ContextBuilder; nothing writes to them after application start.

## 4 Implementation Details

The implementation is organised into five functional areas: core data models, game state management, LLM integration, LLM role separation, and data management.

### 4.1 Core Data Models

All game entities are implemented as Python `dataclass` objects in the `models/` package. The base combatant class, `Entity`, computes derived statistics at construction time:

```
hp          = race.base_hp + archetype.hp_mod
AC          = race.base_AC + archetype.AC_mod
spell_slots = race.base_spell_slots + archetype.spell_slot_mod
```

Computed properties `merged_attacks`, `merged_spells`, `merged_resistances`, `merged_immunities`, and `merged_vulnerabilities` union and deduplicate contributions from the `Race`, `Archetype`, equipped `Weapon`s, and the entity's own known lists. `Entity.create()` enforces two hard constraint checks at instantiation time: the chosen archetype must appear in `race.archetype_constraints`, and each equipped weapon must satisfy the archetype's `WeaponConstraints` (proficiency, handling, weight class, delivery, magic type). These raise `ValueError` at creation, not at action resolution.

The `Action` dataclass carries the resolved player intent. Its `type` field maps to an `ActionType` enum; `parameters` carries the action-specific payload; `actor_instance_id` identifies the acting entity; `raw_input` preserves the original player text for logging and narration; and `reasoning` stores the LLM's chain-of-thought, which is logged but never shown to the player. Required parameters per `ActionType` are declared in a single `REQUIRED_PARAMETERS` table in `core/actions.py`—validation is a table lookup rather than scattered conditional logic.

The `Event` dataclass is the audit primitive for all turn occurrences. Its `payload` carries event-specific data; `source` identifies the originating engine component; and `event_id` is a UUID. Events are the single source of truth for a turn: the narration LLM receives only the event list, never raw engine internals. The `Narration` dataclass pairs rendered prose with a `tone` field consumed by front-end components.

Resource terminology is standardised on `spell_slots` for player/enemy spell resources. The event type name `MANA_UPDATED` is retained as a backwards-compatible label, while event payloads expose `spell_slots` as the canonical field.

### 4.2 Game State Machine

The engine implements a four-state machine: `PRE_GAME`, `EXPLORATION`, `ENCOUNTER`, and `POST_GAME`. Transitions are triggered exclusively by validated actions; no LLM call may directly trigger a state change.

**PRE_GAME** accepts party management and dungeon selection actions. The `start` action is gated by three preconditions: at least one player in the party, a dungeon selected, and all players satisfying race–archetype compatibility.

**EXPLORATION** processes movement, room exploration, and rest actions. The `move` action validates that the destination room is directly connected to the current room before emitting `ROOM_ENTERED` and setting `is_visited = True`. Short and long rests are gated by `room.allowed_rests` and the `is_rested` flag to prevent re-resting. Entering a room with an uncleared encounter automatically transitions to ENCOUNTER.

**ENCOUNTER** is a turn-based combat sub-loop. Initiative is rolled (`d20 + modifier`) for all combatants at encounter start and fixed for the encounter's duration. On a player's turn, input passes through the action parser; on an enemy's turn, the `EnemyAILLM` receives a structured encounter summary and returns an `Action` in the same schema. If the enemy AI response fails to parse or fails validation, `fallback_enemy_action` selects the first available attack targeting the lowest-HP player. Attack resolution follows a two-step roll: (1) `d20 + hit_modifiers` vs. target AC determines hit or miss; (2) a damage roll applies resistance (×0.5), vulnerability (×2), or immunity (×0) multipliers before HP deduction. Status effect durations are decremented at end of each actor's turn and removed at zero. The encounter ends when all enemies or all players reach 0 HP.

**POST_GAME** aggregates session statistics—enemies defeated, rooms cleared, damage dealt and received—and passes them to the narration LLM for a closing passage. `ActionType.FINISH` resets all state to `PRE_GAME`.

### 4.3 LLM Integration

The `LLMClient` (`engine/llm_client.py`) is a thin wrapper around the OpenAI SDK. It sends a system-and-user message pair, retries on rate-limit and transient errors with exponential backoff, and records the following metadata per call to `logs/llm_performance.jsonl`:

```json
{
  "request_id": "uuid",
  "role": "action_parser | conversation | narration | enemy_ai",
  "model": "gpt-4o-mini",
  "timestamp": "2026-03-01T14:23:00Z",
  "prompt_tokens": 812,
  "completion_tokens": 94,
  "latency_ms": 1340,
  "success": true,
  "parse_error": false
}
```

The `ContextBuilder` (`agent/context_builder.py`) assembles context payloads from current game state using a priority-ordered section list. Sections are individually token-estimated with a `len(text) / 4` heuristic; if the total exceeds `max_context_tokens`, lower-priority sections are dropped first. The highest-priority sections (`current_state`, `party`, `current_room`, `rules_summary`) are never dropped; conversation `history` and `world_lore` are always dropped first.

### 4.4 LLM Role Implementation

**Action Parser** (`agent/player_parser.py`): Calls the action parser LLM at `temperature=0.0`. The response is parsed with `json.loads()`; failure raises `LLMParseError`, causing an `ERROR` event and neutral re-prompt. A valid response is classified as either a `Clarify` object (disambiguation question delivered to the player without advancing the turn) or an `Action` object passed through `validate_action()`. Inputs that cannot be mapped to any legal action fall back to `{"type": "query"}`.

**Conversation Responder** (`agent/agent_manager.py` with `agent/memory.py`): Handles `QUERY` and `CONVERSE` action types, both of which bypass deterministic resolution. `QUERY` answers factually from the context payload only; the prompt prohibits asserting facts not present in the supplied context. `CONVERSE` engages the rolling conversation history window and adopts an NPC or GM narrator persona. Neither action type may emit or imply game state changes.

**Narration Generator** (`agent/narrator.py`): Receives the full event list for a turn as a JSON array. Events that constitute a single logical beat (e.g., `ATTACK_HIT` + `DAMAGE_APPLIED` + `DEATH`) are merged into a single sentence. The prompt specifies second-person present tense and prohibits raw numeric stat disclosure. The LLM returns both `text` and a `tone` field (`tense`, `triumphant`, `ominous`) for use by front-end consumers. Events from a full combat round may be batched into one call to produce a cohesive passage, and streaming is used so text begins rendering before the full completion arrives.

**Enemy AI** (`agent/enemy_ai.py`): Receives a structured JSON payload containing the acting enemy's stats and persona description, the current encounter state, and the list of legal actions. Responds with an `Action` object in the same schema used by the player action parser, with `actor_instance_id` set to the enemy's instance ID.

### 4.5 Data Management

Static game data is stored as JSON files under `data/` and validated against JSON Schema definitions in `data/schemata/` at application start, ensuring that malformed definitions are surfaced before any game session begins. In-memory indexed registries (`registry/`) expose typed `get_by_id()` and `list_all()` interfaces for each entity type: `Race`, `Archetype`, `Weapon`, `Attack`, `Spell`, `StatusEffect`, `Enemy`, and `Dungeon`.

A key design decision separates *definition* from *instance* to prevent session state pollution. Each JSON definition carries a stable `id` (e.g., `"plr_elf_ranger_01"`), while runtime combatants receive a separate `instance_id` (e.g., `"plr_inst_8f3a2"`). This allows the same player template to appear in multiple concurrent sessions without ID collision, and allows the event log to unambiguously identify which instance performed each action. Entity construction is centralised in `util/entity_factory.py`, which resolves definition IDs through the registries, applies race-and-archetype stat computation, validates all constraints, and returns a fully initialised `Player` or `Enemy` instance.

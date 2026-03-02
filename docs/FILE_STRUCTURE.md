# File Structure
```
engine/
    game_loop.py
    state_manager.py
    ui/
    rendering/
    input/
    llm_client.py        # low-level API wrapper only

agent/
    agent_manager.py
    narrator.py
    enemy_ai.py
    player_parser.py
    context_builder.py
    memory.py

core/
    models/
    states/
    action.py
    validation_engine.py
    resolution_engine.py
    rules/

data/
tests/
logs/
docs/
```
## 3 layer mental model (engine-agent-core)
| Layer       | One-Sentence Definition        |
| ----------- | ------------------------------ |
| **engine/** | How the program runs           |
| **agent/**  | Who decides what should happen |
| **core/**   | What actually happens          |

## master decision table (engine-agent-core)
| If the code answers the question…     | Put it in                            | Why                      |
| ------------------------------------- | ------------------------------------ | ------------------------ |
| How does the game loop run?           | `engine/`                            | Execution infrastructure |
| How are states switched?              | `engine/`                            | Generic mechanism        |
| How do we render UI?                  | `engine/`                            | Presentation layer       |
| How do we capture input?              | `engine/`                            | I/O handling             |
| How do we call OpenAI / Anthropic?    | `engine/` (or low-level in `agent/`) | External API integration |
| How do we build prompts?              | `agent/`                             | Intelligence layer       |
| How do we maintain narrative memory?  | `agent/`                             | Context reasoning        |
| How do enemies decide what to do?     | `agent/`                             | AI decision-making       |
| How do we interpret player text?      | `agent/`                             | Semantic interpretation  |
| Is an action allowed?                 | `core/`                              | Game rule                |
| What happens when an action executes? | `core/`                              | State mutation           |
| How does damage get calculated?       | `core/`                              | Deterministic rule       |
| What is the player’s HP?              | `core/`                              | Domain state             |
| What defines win/lose?                | `core/`                              | Game logic               |
| Can this run without an LLM?          | `core/`                              | Must be deterministic    |

## Guide
### Rule 1 — Determinism Test
If it must be deterministic and replayable → core/
Examples:
- Combat math
- Inventory updates
- Status effects
- Turn resolution

Core should be testable with pure unit tests and no AI.

### Rule 2 — Intelligence Test
If it decides what should happen next → agent/
Examples:
- Choosing an enemy action
- Interpreting vague player input
- Generating narration
- Building LLM prompts
- Maintaining memory/context

Agent proposes actions.
It does not enforce rules.

### Rule 3 — Infrastructure Test
If it manages execution flow or external systems → engine/
Examples:
- Game loop
- State manager
- Rendering
- Input
- Saving/loading
- API HTTP calls

Engine runs the machine.

## Dependency Rule
```
engine  →  agent  →  core
```








# core/-engine/ Decision table
| If it answers the question…                      | Put it in | Why                          |
| ------------------------------------------------ | --------- | ---------------------------- |
| “How does the game loop run?”                    | `engine/` | Infrastructure               |
| “How do we switch states?”                       | `engine/` | Generic mechanism            |
| “How do we render things?”                       | `engine/` | Rendering is infrastructure  |
| “How do we get input?”                           | `engine/` | Input system is generic      |
| “How do we call the LLM?”                        | `engine/` | External service integration |
| “How do we parse raw text into structured data?” | `engine/` | Parsing is infrastructure    |
| “Is this action allowed in the game world?”      | `core/`   | Game rule                    |
| “What happens when the player attacks?”          | `core/`   | Game logic                   |
| “How does health decrease?”                      | `core/`   | Domain logic                 |
| “Does the player win?”                           | `core/`   | Game rule                    |
| “What is a valid move in this game?”             | `core/`   | Game-specific                |

Put it in engine/ if:
- It manages execution
- It talks to external systems
- It is generic infrastructure
- It does not care what the game rules are

Put it in core/ if:
- It defines the game world
## Dependency Rule
```
engine  →  agent  →  core
```

Allowed imports should follow the same direction:
- `engine/` may import from `agent/` and `core/`
- `agent/` may import from `core/` but not from `engine/`
- `core/` must not import from `agent/` or `engine/`
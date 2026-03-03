# File Structure
```
engine/
    game_loop.py
    state_manager.py
    ui/
    rendering/
    input/
    # File Structure

    ## Current source-of-truth layout
    ```
    engine/
        game_state.py        # compatibility shim re-exporting from core.states

    agent/
        # (planned LLM-facing orchestration layer)

    core/
        actions.py
        dice.py
        enums.py
        events.py
        narration.py
        rules.py
        models/              # source-of-truth domain models
        registry/            # source-of-truth data loaders/indexes
        states/              # source-of-truth game state machine + handlers


    data/
    tests/
    logs/
    docs/
 ```

## 3-layer mental model (engine-agent-core)
| Layer | One-sentence definition |
| --- | --- |
| **engine/** | How the program runs (looping, orchestration, infrastructure) |
| **agent/** | Who decides what should happen (LLM interpretation/planning) |
| **core/** | What actually happens (deterministic rules + state mutation) |

## Placement rules
| If the code answers the question… | Put it in | Why |
| --- | --- | --- |
| How does the game loop run? | `engine/` | Execution infrastructure |
| How are states switched? | `core/states/` (state behavior) + `engine/` (orchestration) | Deterministic behavior in core, runtime wiring in engine |
| How do we call OpenAI/Anthropic? | `engine/` (transport) and/or `agent/` (role-specific clients) | External integration |
| How do we build prompts / parse intent? | `agent/` | Intelligence layer |
| Is an action allowed? | `core/` | Game rule |
| What happens when an action executes? | `core/` | State mutation |
| Can this run without an LLM? | `core/` | Must be deterministic and replayable |

## Dependency rule
```
engine  →  agent  →  core
```

Allowed imports:
- `engine/` may import from `agent/` and `core/`
- `agent/` may import from `core/` but not from `engine/`
- `core/` must not import from `agent/` or `engine/`

## Migration status
- `core/models`, `core/registry`, and `core/states` are now canonical.
- Top-level `models/` and `registry/` are temporary compatibility shims.
- New code should import from `core.models.*`, `core.registry.*`, and `core.states.*`.
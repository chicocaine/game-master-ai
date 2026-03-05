# TODO
> Single source-of-truth roadmap for implementation status and next milestones.

## Status Snapshot (as of 2026-03-06)

### ✅ Completed Foundation
- [x] Canonical core contracts (`Action`, `Event`, state machine, deterministic resolution)
- [x] Data models + JSON schemata + data loading/validation pipeline
- [x] Deterministic gameplay handlers across pregame/exploration/encounter/postgame
- [x] Engine runtime skeleton (`engine/game_loop.py`, `engine/state_manager.py`)
- [x] Agent skeleton (`agent/player_parser.py`, `agent/narrator.py`, `agent/enemy_ai.py`, `agent/context_builder.py`)
- [x] Clarify flow with no-turn-advance behavior
- [x] Runtime logging + LLM performance record contract
- [x] Automated tests for core/engine/agent/LLM client skeleton
- [x] Expanded context builder payload (current room, legal actions, dungeon progress, turn context, status effects)
- [x] Pregame context builder for party construction (race/archetype/weapon options) and dungeon selection readiness
- [x] Narration event batching utility for cohesive turn-level narration prompts
- [x] JSON schema validation for LLM action/enemy payloads
- [x] Prompt templates upgraded with few-shot examples
- [x] Role-specific temperature and max-token configuration
- [x] Evaluation harness scaffolding and metric tests
- [x] Test suite baseline updated and passing (`155 passed`)

### 🚧 In Progress
- [ ] Live LLM smoke validation + prompt tuning pass from real outputs
- [x] Observability linking between runtime turn logs and LLM performance records

## Active Milestones

### M1 — Live LLM Runtime Wiring
- [x] Load `.env` / environment config for model, key, and inference parameters
- [x] Implement provider transport adapter for `LLMClient`
- [x] Add role prompt templates under `agent/prompts/`
- [x] Wire `AgentManager` roles to LLM-backed parser/narrator/enemy selector with deterministic fallback behavior
- [x] Add a runnable `main.py` CLI loop for local end-to-end play

### M2 — Prompting and Response Contracts
- [x] Enforce strict JSON contract for parser and enemy AI responses
- [x] Add robust fallback on malformed JSON and clarify retries
- [x] Define prompt tuning workflow and sample prompt fixtures

### M3 — Evaluation and Observability
- [x] Add deterministic replay harness for turn logs
- [x] Add prompt/response trace IDs linking turn logs to LLM performance logs
- [x] Add lightweight scenario-based evaluation script (parser accuracy, invalid-action rate, clarify rate)
- [x] Add live performance report script (P50/P95 latency per role from JSONL logs)

### M4 — Documentation (doc drift) + Cleanup
- [ ] Remove deprecated/duplicate helper paths and confirm canonical imports (`core.*`)
- [ ] Check for and remove or resolve unused/unreferenced enums, files, scripts and functions
- [ ] Replace stale docs sections with current architecture/runtime behavior
- [x] Expand `README.md` with setup, run, and test instructions

## Next Step (Immediate)
- [x] Run live smoke session with `python main.py --live-llm` using `.env`
- [x] Capture and review parser/narration outputs from logs
- [ ] Tune few-shot examples and schema constraints based on real failure cases
- [x] Add deterministic turn-log replay script for debugging and regression workflows

## Backlog (Post-MVP)
- [ ] Dungeon systems expansion (inventory, traps, dynamic events, random encounters, NPC interactions)
- [ ] Advanced memory systems for long-running sessions
- [ ] UI layer beyond CLI


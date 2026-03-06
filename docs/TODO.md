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
- [x] Pre-UI debug CLI layer under `engine/cli` with labeled output for narration, parsed action payloads, action type, and turn trace context
- [x] Test suite baseline updated and passing (`155 passed`)

### 🚧 In Progress
- [x] Live LLM smoke validation + prompt tuning pass from real outputs
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

### M5 — Developer CLI Testing (Player Play-Test Readiness)
- [x] Add CLI preflight check script (env present, API key set, data files load, log paths writable)
- [x] Add deterministic CLI test script (`main.py` without `--live-llm`) for pregame → exploration → encounter → postgame flow
- [x] Add live CLI smoke script (`main.py --live-llm`) with scripted 5–10 turn session
- [x] Verify pregame party build flow in CLI (create/remove player, choose dungeon, start gating)
- [x] Verify clarify loop UX in CLI (no turn advance, option selection works)
- [x] Verify enemy turn behavior in CLI (legal action + fallback to `end_turn`)
- [x] Verify logs are correlated per turn (`trace_id`, `session_id`, `llm_request_id`)
- [x] Verify replay workflow from produced logs (`scripts/replay_turn_log.py`)
- [x] Add pass/fail play-test checklist document under `docs/` with known issues and repro steps
- [x] Add one-command CLI suite runner (`scripts/cli_test_suite.py`) for M5 readiness checks
- [x] Move CLI rendering/labels into `engine/cli` helpers for debugging-oriented terminal UX

Acceptance criteria:
- [x] A developer can run one deterministic and one live scripted play-test end-to-end with zero crashes
- [x] CLI output, runtime logs, and LLM logs are sufficient to reconstruct each tested turn
- [x] Any failed turns include actionable error/validation feedback

## Next Step (Immediate)
- [x] Run live smoke session with `python main.py --live-llm` using `.env`
- [x] Capture and review parser/narration outputs from logs
- [x] Tune few-shot examples and schema constraints based on real failure cases
- [x] Add deterministic turn-log replay script for debugging and regression workflows
- [x] Execute M5 developer CLI play-test checklist and publish first pass/fail report (`docs/CLI_PLAYTEST_REPORT.md`)

## Follow-up Improvements
- [x] Add JSON export mode to `scripts/cli_test_suite.py` for CI/report automation
- [x] Expand scripted live CLI run to 5–10 turns for longer-session stability and prompt drift checks

## Backlog (Post-MVP)
- [ ] Dungeon systems expansion (inventory, traps, dynamic events, random encounters, NPC interactions)
- [ ] Advanced memory systems for long-running sessions
- [ ] UI layer beyond CLI


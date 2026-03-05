# CLI Play-Test Report (Pass 1)

Date: 2026-03-06
Scope: Developer CLI readiness checks and scripted play-test execution.

## Executed Commands
- `python scripts/cli_preflight.py`
- `python scripts/cli_test_deterministic.py`
- `python scripts/cli_test_live_smoke.py`
- `python scripts/replay_turn_log.py <latest_turn_log> --strict-events`
- `python -m pytest -q`
- `python scripts/cli_test_pregame_gating.py`
- `python scripts/cli_test_clarify_flow.py`
- `python scripts/cli_test_enemy_turn.py`
- `python scripts/cli_test_suite.py`
- `python scripts/cli_test_suite.py --json-out logs/sessions/cli_suite_report.json`

## Results

### Preflight
- Status: PASS
- Notes:
  - `LLM_API_KEY` present
  - Data templates load successfully
  - `logs/sessions` writable

### Deterministic CLI Scripted Test
- Status: PASS
- Evidence:
  - CLI starts successfully
  - Scripted pregame actions execute (`create_player`, `choose_dungeon`, `start`)
  - Turn log produced

### Live CLI Smoke Scripted Test
- Status: PASS
- Evidence:
  - CLI starts with live mode
  - Scripted query turn executes and exits cleanly

### Log Correlation
- Status: PASS
- Evidence:
  - `trace_id`, `session_id`, and `llm_request_id` are present across runtime and LLM logs for tested turns

### Replay Workflow
- Status: PASS
- Evidence:
  - Replay summary reports zero turn mismatches and zero event-set mismatches on latest deterministic run

### Test Suite Health
- Status: PASS
- Evidence:
  - `155 passed`

## Checklist Summary (M5)
- PASS:
  - CLI preflight script
  - Deterministic scripted CLI test
  - Live scripted CLI smoke test
  - Log correlation verification
  - Replay workflow verification
  - Pregame `remove_player` and strict start-gating negative-path CLI scenario
  - Clarify UX verification via scripted CLI transcript scenario
  - Enemy-turn legal + fallback verification in scripted runtime scenario

## Pass 2 Addendum

### Pregame Gating Scenario
- Status: PASS
- Evidence:
  - Rejected `start` before setup
  - `remove_player` flow observed
  - Successful `start` after player+dungeon setup

### Clarify UX Scenario
- Status: PASS
- Evidence:
  - First clarify turn does not advance turn
  - Option selection resolves to actionable query and advances turn

### Enemy Turn Scenario
- Status: PASS
- Evidence:
  - Legal enemy turn executes with events
  - Forced selector error emits rejection and falls back to `end_turn`

### Aggregated M5 Suite
- Status: PASS
- Evidence:
  - One-command suite runner executes all six CLI checks
  - Summary reports `total=6`, `passed=6`, `failed=0`
  - JSON report export written to `logs/sessions/cli_suite_report.json`

## Next Actions
1. Expand scripted live CLI run to 5–10 turns for longer-session stability and prompt drift checks.

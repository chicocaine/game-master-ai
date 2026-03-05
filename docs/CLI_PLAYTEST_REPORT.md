# CLI Play-Test Report (Pass 1)

Date: 2026-03-06
Scope: Developer CLI readiness checks and scripted play-test execution.

## Executed Commands
- `python scripts/cli_preflight.py`
- `python scripts/cli_test_deterministic.py`
- `python scripts/cli_test_live_smoke.py`
- `python scripts/replay_turn_log.py <latest_turn_log> --strict-events`
- `python -m pytest -q`

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
- PARTIAL / TODO:
  - Clarify UX verification via CLI transcript-focused scenario
  - Enemy-turn fallback verification in scripted CLI scenario
  - Pregame `remove_player` and strict start-gating negative-path CLI scenario

## Next Actions
1. Add deterministic scripted scenario that intentionally triggers clarify flow and validates no turn advance in CLI logs.
2. Add scripted enemy-turn scenario that forces selector fallback path and checks emitted rejection + `end_turn` behavior.
3. Add negative pregame start-gating script (`start` before selecting dungeon/party) and assert actionable rejection output.

# Engine + Agent Implementation Kickoff Checklist

> Scope: implement runtime engine and agent orchestration on top of current canonical core contracts.

## 0) Canonical Contract Lock (Do Not Drift)

- [x] Use `Action` from `core/actions.py` as the single parsed-action contract.
- [x] Keep canonical parameter names:
  - [x] `target_instance_ids`
  - [x] `race`, `archetype`, `weapons`
  - [x] `spell_slots` (resource terminology)
- [x] Treat `MANA_UPDATED` / `mana_updated` as legacy event label; payload canonical is `spell_slots`.
- [x] Keep compatibility aliases only at normalization boundary (already in `core/actions.py`).

## 1) Engine Runtime Skeleton (Minimal)

- [x] Create `engine/game_loop.py` with a thin loop:
  1. read input
  2. parse to `Action` (agent placeholder)
  3. call `apply_action(...)`
  4. render events/narration output
- [x] Create `engine/state_manager.py` for session lifecycle helpers only:
  - [x] initialize `GameSessionState`
  - [x] load templates once
  - [x] reset/finish hooks
- [x] Keep engine orchestration-only; no rules duplication from `core/`.

Acceptance criteria:
- [x] A non-LLM local loop can run pregame -> exploration -> encounter -> postgame using deterministic actions.
- [x] No engine module mutates state except via `apply_action(...)`.

## 2) Agent Layer Skeleton (Minimal)

- [x] Create minimal `agent/agent_manager.py` with role routing only:
  - [x] action parsing role
  - [x] narration role
  - [x] conversation/query role
  - [x] enemy-action role
- [x] Create `agent/context_builder.py` to provide compact state summaries.
- [x] Create `agent/player_parser.py` that outputs valid `Action` dict payloads.
- [x] Create `agent/narrator.py` that converts event lists to text.
- [x] Create `agent/enemy_ai.py` for enemy action selection.

Acceptance criteria:
- [x] Agent output never mutates state directly.
- [x] All state mutation still happens through core validation + resolution path.

## 3) Engine-Agent Integration Contract

- [x] Engine sends raw player input + summarized context to agent parser.
- [x] Parser returns either:
  - [x] valid action payload (convert via `Action.from_dict(...)`), or
  - [x] clarification response object (no turn advance).
- [x] Engine validates and resolves using:
  - [x] `validate_action_with_details(...)`
  - [x] `apply_action(...)`
- [x] Narrator consumes emitted events only.

Acceptance criteria:
- [x] Invalid parser output becomes explicit rejection/clarify flow.
- [x] Turn order does not advance on parser failure/clarify.

## 4) Clarify Flow (MVP)

- [x] Define a minimal clarify object in agent layer only (no core state mutation):

```json
{
  "type": "clarify",
  "ambiguous_field": "target_instance_ids",
  "question": "Who do you want to target?",
  "options": [
    {"label": "Skeleton A", "value": "enm_inst_01"},
    {"label": "Skeleton B", "value": "enm_inst_02"}
  ]
}
```

- [x] Engine handles clarify as a prompt-to-user response and re-prompts same actor.

Acceptance criteria:
- [x] No state mutation or turn advance for clarify responses.

## 5) Logging + Observability (Minimal)

- [x] Ensure each submitted action and resulting events are logged.
- [x] Log parser failures and validation failures distinctly.
- [x] Include role + latency metadata for each LLM call when LLM integration starts.

Acceptance criteria:
- [x] A single turn can be reconstructed from logs (input -> action -> events -> output text).

## 6) Test Plan for Implementation Phase

- [x] Add engine loop smoke test (mock parser output).
- [x] Add clarify non-advance test.
- [x] Add parser-invalid-json fallback test.
- [x] Add enemy turn fallback action test.
- [x] Add integration test for spell resource update payload:
  - [x] event label `mana_updated`
  - [x] payload includes `spell_slots`.

Acceptance criteria:
- [x] New engine/agent tests pass without altering existing core test expectations.

## 7) Sequencing (Recommended)

1. Engine loop + state manager stubs
2. Agent manager + parser/narrator stubs
3. Clarify flow wiring
4. Enemy AI fallback path
5. Logging instrumentation
6. Integration tests

## 8) Out-of-Scope for MVP

- Advanced memory systems
- Multi-model orchestration
- UI redesign
- Additional game mechanics beyond current canonical rules

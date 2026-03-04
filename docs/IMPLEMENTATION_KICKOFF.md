# Engine + Agent Implementation Kickoff Checklist

> Scope: implement runtime engine and agent orchestration on top of current canonical core contracts.

## 0) Canonical Contract Lock (Do Not Drift)

- [ ] Use `Action` from `core/actions.py` as the single parsed-action contract.
- [ ] Keep canonical parameter names:
  - [ ] `target_instance_ids`
  - [ ] `race`, `archetype`, `weapons`
  - [ ] `spell_slots` (resource terminology)
- [ ] Treat `MANA_UPDATED` / `mana_updated` as legacy event label; payload canonical is `spell_slots`.
- [ ] Keep compatibility aliases only at normalization boundary (already in `core/actions.py`).

## 1) Engine Runtime Skeleton (Minimal)

- [ ] Create `engine/game_loop.py` with a thin loop:
  1. read input
  2. parse to `Action` (agent placeholder)
  3. call `apply_action(...)`
  4. render events/narration output
- [ ] Create `engine/state_manager.py` for session lifecycle helpers only:
  - [ ] initialize `GameSessionState`
  - [ ] load templates once
  - [ ] reset/finish hooks
- [ ] Keep engine orchestration-only; no rules duplication from `core/`.

Acceptance criteria:
- [ ] A non-LLM local loop can run pregame -> exploration -> encounter -> postgame using deterministic actions.
- [ ] No engine module mutates state except via `apply_action(...)`.

## 2) Agent Layer Skeleton (Minimal)

- [ ] Create minimal `agent/agent_manager.py` with role routing only:
  - [ ] action parsing role
  - [ ] narration role
  - [ ] conversation/query role
  - [ ] enemy-action role
- [ ] Create `agent/context_builder.py` to provide compact state summaries.
- [ ] Create `agent/player_parser.py` that outputs valid `Action` dict payloads.
- [ ] Create `agent/narrator.py` that converts event lists to text.
- [ ] Create `agent/enemy_ai.py` for enemy action selection.

Acceptance criteria:
- [ ] Agent output never mutates state directly.
- [ ] All state mutation still happens through core validation + resolution path.

## 3) Engine-Agent Integration Contract

- [ ] Engine sends raw player input + summarized context to agent parser.
- [ ] Parser returns either:
  - [ ] valid action payload (convert via `Action.from_dict(...)`), or
  - [ ] clarification response object (no turn advance).
- [ ] Engine validates and resolves using:
  - [ ] `validate_action_with_details(...)`
  - [ ] `apply_action(...)`
- [ ] Narrator consumes emitted events only.

Acceptance criteria:
- [ ] Invalid parser output becomes explicit rejection/clarify flow.
- [ ] Turn order does not advance on parser failure/clarify.

## 4) Clarify Flow (MVP)

- [ ] Define a minimal clarify object in agent layer only (no core state mutation):

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

- [ ] Engine handles clarify as a prompt-to-user response and re-prompts same actor.

Acceptance criteria:
- [ ] No state mutation or turn advance for clarify responses.

## 5) Logging + Observability (Minimal)

- [ ] Ensure each submitted action and resulting events are logged.
- [ ] Log parser failures and validation failures distinctly.
- [ ] Include role + latency metadata for each LLM call when LLM integration starts.

Acceptance criteria:
- [ ] A single turn can be reconstructed from logs (input -> action -> events -> output text).

## 6) Test Plan for Implementation Phase

- [ ] Add engine loop smoke test (mock parser output).
- [ ] Add clarify non-advance test.
- [ ] Add parser-invalid-json fallback test.
- [ ] Add enemy turn fallback action test.
- [ ] Add integration test for spell resource update payload:
  - [ ] event label `mana_updated`
  - [ ] payload includes `spell_slots`.

Acceptance criteria:
- [ ] New engine/agent tests pass without altering existing core test expectations.

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

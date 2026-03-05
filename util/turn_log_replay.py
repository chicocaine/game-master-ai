from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.actions import Action
from core.states.session import GameSessionState
from engine.game_state import apply_action
from engine.state_manager import EngineStateManager


@dataclass(frozen=True)
class ReplaySummary:
    total_records: int
    actionable_records: int
    replayed_records: int
    skipped_records: int
    mismatched_turns: int
    mismatched_event_sets: int


def load_turn_records(path: str | Path) -> List[Dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []

    records: List[Dict[str, Any]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        row = line.strip()
        if not row:
            continue
        parsed = json.loads(row)
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def is_actionable_record(record: Dict[str, Any]) -> bool:
    parsed = record.get("parsed")
    if not isinstance(parsed, dict):
        return False

    action_type = str(parsed.get("type", "")).strip().lower()
    if not action_type or action_type == "clarify":
        return False

    if bool(record.get("parser_failed", False)):
        return False

    return True


def replay_turn_log(
    turn_log_path: str | Path,
    session: GameSessionState,
    strict_event_check: bool = False,
) -> ReplaySummary:
    records = load_turn_records(turn_log_path)
    actionable = [record for record in records if is_actionable_record(record)]

    replayed_records = 0
    skipped_records = 0
    mismatched_turns = 0
    mismatched_event_sets = 0

    for record in actionable:
        parsed = record.get("parsed", {})
        if not isinstance(parsed, dict):
            skipped_records += 1
            continue

        try:
            action = Action.from_dict(parsed)
        except Exception:
            skipped_records += 1
            continue

        turn_before = session.turn
        replay_events = apply_action(session, action)
        replayed_records += 1

        expected_turn_after = int(record.get("turn_after", turn_before))
        if session.turn != expected_turn_after:
            mismatched_turns += 1

        if strict_event_check:
            expected_events = record.get("events", []) if isinstance(record.get("events", []), list) else []
            expected_names = [
                str(event.get("name", ""))
                for event in expected_events
                if isinstance(event, dict)
            ]
            replay_names = [event.name for event in replay_events]
            if expected_names != replay_names:
                mismatched_event_sets += 1

    return ReplaySummary(
        total_records=len(records),
        actionable_records=len(actionable),
        replayed_records=replayed_records,
        skipped_records=skipped_records,
        mismatched_turns=mismatched_turns,
        mismatched_event_sets=mismatched_event_sets,
    )


def replay_turn_log_from_fresh_session(
    turn_log_path: str | Path,
    data_dir: str | Path = "data",
    strict_event_check: bool = False,
) -> ReplaySummary:
    manager = EngineStateManager(data_dir)
    session = manager.create_session()
    return replay_turn_log(
        turn_log_path=turn_log_path,
        session=session,
        strict_event_check=strict_event_check,
    )

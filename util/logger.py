from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.enums import GameState
from core.events import Event


_LOG_ROOT = Path(__file__).resolve().parent.parent / "logs"
_EVENTS_DIR = _LOG_ROOT / "events"
_SESSIONS_DIR = _LOG_ROOT / "sessions"
_ERRORS_DIR = _LOG_ROOT / "errors"

def _ensure_dirs() -> None:
    for d in (_EVENTS_DIR, _SESSIONS_DIR, _ERRORS_DIR):
        d.mkdir(parents=True, exist_ok=True)

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

def _write_json(path: Path, record: dict) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

# Event Logger
class EventLogger:

    def __init__(self, session_id: str) -> None:
        _ensure_dirs()
        self.session_id = session_id
        self._path = _EVENTS_DIR / f"{session_id}.jsonl"

    def log(self, event: Event) -> None:
        record = event.to_dict()
        record["session_id"] = self.session_id
        _append_jsonl(self._path, record)

    def log_many(self, events: List[Event]) -> None:
        for event in events:
            self.log(event)


    @property
    def path(self) -> Path:
        return self._path


# Session Logger
@dataclass
class SessionRecord:
    session_id: str
    started_at: str = field(default_factory=_utc_now_iso)
    ended_at: Optional[str] = None
    dungeon_id: Optional[str] = None
    dungeon_name: Optional[str] = None
    party: List[Dict[str, Any]] = field(default_factory=list)
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    outcome: Optional[str] = None        # "victory" | "defeat" | "abandoned"
    summary_stats: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "dungeon_id": self.dungeon_id,
            "dungeon_name": self.dungeon_name,
            "party": self.party,
            "state_history": self.state_history,
            "outcome": self.outcome,
            "summary_stats": self.summary_stats,
            "metadata": self.metadata,
        }


class SessionLogger:

    def __init__(self, session_id: Optional[str] = None) -> None:
        _ensure_dirs()
        self.session_id = session_id or str(uuid4())
        self._path = _SESSIONS_DIR / f"{self.session_id}.json"
        self._record = SessionRecord(session_id=self.session_id)
        self._flush()

    def set_dungeon(self, dungeon_id: str, dungeon_name: str) -> None:
        self._record.dungeon_id = dungeon_id
        self._record.dungeon_name = dungeon_name
        self._flush()

    def set_party(self, party: List[Dict[str, Any]]) -> None:
        self._record.party = party
        self._flush()

    def log_state_transition(
        self,
        from_state: GameState,
        to_state: GameState,
        reason: str = "",
    ) -> None:
        self._record.state_history.append({
            "from": from_state.value,
            "to": to_state.value,
            "reason": reason,
            "timestamp": _utc_now_iso(),
        })
        self._flush()

    def end_session(
        self,
        outcome: str,
        summary_stats: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._record.ended_at = _utc_now_iso()
        self._record.outcome = outcome
        if summary_stats:
            self._record.summary_stats.update(summary_stats)
        if metadata:
            self._record.metadata.update(metadata)
        self._flush()

    def update_stats(self, stats: Dict[str, Any]) -> None:
        self._record.summary_stats.update(stats)
        self._flush()

    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        self._record.metadata.update(metadata)
        self._flush()


    def _flush(self) -> None:
        _write_json(self._path, self._record.to_dict())


    @property
    def path(self) -> Path:
        return self._path

    @property
    def record(self) -> SessionRecord:
        return self._record


# Error Log
class ErrorLogger:

    _GLOBAL_PATH = _ERRORS_DIR / "errors.jsonl"

    def __init__(self, session_id: Optional[str] = None) -> None:
        _ensure_dirs()
        self.session_id = session_id
        self._session_path: Optional[Path] = (
            _ERRORS_DIR / f"{session_id}.jsonl" if session_id else None
        )

    def log(
        self,
        message: str,
        error_type: str = "error",
        exc: Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        record: Dict[str, Any] = {
            "error_id": str(uuid4()),
            "session_id": self.session_id,
            "error_type": error_type,
            "message": message,
            "timestamp": _utc_now_iso(),
            "traceback": traceback.format_exc() if exc else None,
            "context": context or {},
        }
        _append_jsonl(self._GLOBAL_PATH, record)
        if self._session_path is not None:
            _append_jsonl(self._session_path, record)

    def log_exc(
        self,
        exc: BaseException,
        message: str = "",
        error_type: str = "exception",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.log(
            message=message or str(exc),
            error_type=error_type,
            exc=exc,
            context=context,
        )

    @property
    def global_path(self) -> Path:
        return self._GLOBAL_PATH

    @property
    def session_path(self) -> Optional[Path]:
        return self._session_path
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeTurnLogger:
    def __init__(self, session_id: str, log_dir: str | Path = "logs/sessions") -> None:
        self.session_id = session_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.log_dir / f"{self.session_id}_turns.jsonl"

    def log_turn(self, record: Dict[str, Any]) -> None:
        payload = dict(record)
        payload.setdefault("session_id", self.session_id)
        payload.setdefault("timestamp", _utc_now_iso())
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    @property
    def path(self) -> Path:
        return self._path

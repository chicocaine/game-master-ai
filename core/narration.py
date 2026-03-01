from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4


def _get_str(data: dict, key: str, default: str = "") -> str:
	return str(data.get(key, default))


def _get_dict(data: dict, key: str) -> Dict[str, Any]:
	value = data.get(key, {})
	if isinstance(value, dict):
		return value
	return {}


def _utc_now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def _normalize_text(text: str) -> str:
	return str(text).strip()


@dataclass
class Narration:
	event_id: str
	text: str
	source: str = "game-master-ai"
	metadata: Dict[str, Any] = field(default_factory=dict)
	timestamp: str = field(default_factory=_utc_now_iso)
	narration_id: str = field(default_factory=lambda: str(uuid4()))

	def to_dict(self) -> dict:
		return {
			"narration_id": self.narration_id,
			"event_id": self.event_id,
			"text": self.text,
			"source": self.source,
			"metadata": self.metadata,
			"timestamp": self.timestamp,
		}

	@classmethod
	def from_dict(cls, data: dict) -> "Narration":
		return cls(
			event_id=_get_str(data, "event_id"),
			text=_normalize_text(_get_str(data, "text")),
			source=_get_str(data, "source", "game-master-ai"),
			metadata=_get_dict(data, "metadata"),
			timestamp=_get_str(data, "timestamp", _utc_now_iso()),
			narration_id=_get_str(data, "narration_id", str(uuid4())),
		)


def validate_narration(narration: Narration) -> List[str]:
	errors: List[str] = []

	if not narration.event_id.strip():
		errors.append("'event_id' is required")

	if not narration.text.strip():
		errors.append("'text' is required")

	return errors


def create_narration(
	event_id: str,
	text: str,
	source: str = "game-master-ai",
	metadata: Dict[str, Any] | None = None,
) -> Narration:
	return Narration(
		event_id=event_id,
		text=_normalize_text(text),
		source=source,
		metadata=metadata or {},
	)

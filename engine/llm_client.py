from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4


class LLMError(Exception):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMParseError(LLMError):
    pass


@dataclass(frozen=True)
class LLMRequest:
    role: str
    system_prompt: str
    user_message: str
    model: str
    max_tokens: int
    temperature: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponseRecord:
    request_id: str
    role: str
    model: str
    timestamp: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    parse_success: bool
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "role": self.role,
            "model": self.model,
            "timestamp": self.timestamp,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "parse_success": self.parse_success,
            "metadata": dict(self.metadata),
        }


class LLMClient:
    def __init__(
        self,
        transport: Callable[[LLMRequest], Dict[str, Any]],
        log_path: str | Path = "logs/sessions/llm_performance.jsonl",
    ) -> None:
        self.transport = transport
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def complete(self, request: LLMRequest, parse_json: bool = False) -> Dict[str, Any]:
        request_id = str(uuid4())
        started = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()
        parse_success = False

        try:
            response = self.transport(request)
        except TimeoutError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            self._write_record(
                LLMResponseRecord(
                    request_id=request_id,
                    role=request.role,
                    model=request.model,
                    timestamp=timestamp,
                    latency_ms=latency_ms,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    parse_success=False,
                    metadata={**request.metadata, "error": "timeout"},
                )
            )
            raise LLMTimeoutError(str(exc)) from exc

        latency_ms = (time.perf_counter() - started) * 1000
        text = str(response.get("text", ""))
        usage = response.get("usage", {}) if isinstance(response.get("usage", {}), dict) else {}
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)

        payload: Dict[str, Any] = {
            "request_id": request_id,
            "text": text,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "raw": response,
        }

        if parse_json:
            try:
                payload["parsed"] = json.loads(text)
                parse_success = True
            except json.JSONDecodeError as exc:
                self._write_record(
                    LLMResponseRecord(
                        request_id=request_id,
                        role=request.role,
                        model=request.model,
                        timestamp=timestamp,
                        latency_ms=latency_ms,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        parse_success=False,
                        metadata={**request.metadata, "error": "parse"},
                    )
                )
                raise LLMParseError(str(exc)) from exc
        else:
            parse_success = True

        self._write_record(
            LLMResponseRecord(
                request_id=request_id,
                role=request.role,
                model=request.model,
                timestamp=timestamp,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                parse_success=parse_success,
                metadata=request.metadata,
            )
        )
        return payload

    def _write_record(self, record: LLMResponseRecord) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

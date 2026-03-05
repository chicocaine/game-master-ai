from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def load_llm_records(path: str | Path) -> List[Dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []

    records: List[Dict[str, Any]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def summarize_latency(records: List[Dict[str, Any]], session_id: str | None = None) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[float]] = defaultdict(list)
    parse_success: Dict[str, List[int]] = defaultdict(list)

    for record in records:
        metadata = record.get("metadata", {}) if isinstance(record.get("metadata", {}), dict) else {}
        if session_id and str(metadata.get("session_id", "")) != session_id:
            continue

        role = str(record.get("role", "unknown"))
        latency = float(record.get("latency_ms", 0.0) or 0.0)
        grouped[role].append(latency)
        parse_success[role].append(1 if bool(record.get("parse_success", False)) else 0)

    summary: Dict[str, Dict[str, float]] = {}
    for role, latencies in grouped.items():
        ordered = sorted(latencies)
        n = len(ordered)
        p50_index = int(round(0.5 * (n - 1)))
        p95_index = int(round(0.95 * (n - 1)))
        successes = parse_success.get(role, [])

        summary[role] = {
            "count": float(n),
            "avg_latency_ms": sum(ordered) / n,
            "p50_latency_ms": ordered[p50_index],
            "p95_latency_ms": ordered[p95_index],
            "parse_success_rate": (sum(successes) / len(successes)) if successes else 0.0,
        }

    return summary

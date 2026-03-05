from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, List


ParserCallable = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass(frozen=True)
class EvalMetrics:
    total_cases: int
    action_type_accuracy: float
    parameter_exact_match: float
    parameter_partial_match: float
    parse_success_rate: float
    validation_pass_rate: float
    avg_latency_ms: float
    p95_latency_ms: float


def load_golden_actions(path: str | Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def run_eval(cases: List[Dict[str, Any]], parser: ParserCallable) -> EvalMetrics:
    if not cases:
        return EvalMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    action_type_hits = 0
    exact_hits = 0
    partial_hits = 0
    parse_success = 0
    validation_pass = 0
    latencies: List[float] = []

    for case in cases:
        started = perf_counter()
        parsed: Dict[str, Any] | None = None
        try:
            parsed = parser(case)
            if isinstance(parsed, dict) and str(parsed.get("type", "")).strip():
                parse_success += 1
        except Exception:
            parsed = None
        latency_ms = (perf_counter() - started) * 1000
        latencies.append(latency_ms)

        if not isinstance(parsed, dict):
            continue

        if parsed.get("type") == case.get("expected_action_type"):
            action_type_hits += 1

        expected_params = case.get("expected_parameters", {})
        got_params = parsed.get("parameters", {}) if isinstance(parsed.get("parameters", {}), dict) else {}
        if isinstance(expected_params, dict):
            exact_match = got_params == expected_params
            partial_match = all(got_params.get(key) == value for key, value in expected_params.items())
            if exact_match:
                exact_hits += 1
            if partial_match:
                partial_hits += 1
                validation_pass += 1

    total = len(cases)
    latencies_sorted = sorted(latencies)
    p95_index = min(len(latencies_sorted) - 1, int(round(0.95 * (len(latencies_sorted) - 1))))

    return EvalMetrics(
        total_cases=total,
        action_type_accuracy=action_type_hits / total,
        parameter_exact_match=exact_hits / total,
        parameter_partial_match=partial_hits / total,
        parse_success_rate=parse_success / total,
        validation_pass_rate=validation_pass / total,
        avg_latency_ms=sum(latencies) / total,
        p95_latency_ms=latencies_sorted[p95_index],
    )


def write_eval_result(metrics: EvalMetrics, path: str | Path) -> None:
    payload = {
        "total_cases": metrics.total_cases,
        "action_type_accuracy": metrics.action_type_accuracy,
        "parameter_exact_match": metrics.parameter_exact_match,
        "parameter_partial_match": metrics.parameter_partial_match,
        "parse_success_rate": metrics.parse_success_rate,
        "validation_pass_rate": metrics.validation_pass_rate,
        "avg_latency_ms": metrics.avg_latency_ms,
        "p95_latency_ms": metrics.p95_latency_ms,
    }

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

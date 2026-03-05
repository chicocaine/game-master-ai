import json

from util.llm_performance_report import load_llm_records, summarize_latency


def test_summarize_latency_by_role_and_session(tmp_path):
    source = tmp_path / "llm_performance.jsonl"
    rows = [
        {
            "role": "action_parser",
            "latency_ms": 100,
            "parse_success": True,
            "metadata": {"session_id": "sess_1"},
        },
        {
            "role": "action_parser",
            "latency_ms": 300,
            "parse_success": False,
            "metadata": {"session_id": "sess_1"},
        },
        {
            "role": "narration",
            "latency_ms": 200,
            "parse_success": True,
            "metadata": {"session_id": "sess_2"},
        },
    ]
    source.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    loaded = load_llm_records(source)
    summary_all = summarize_latency(loaded)
    summary_sess_1 = summarize_latency(loaded, session_id="sess_1")

    assert "action_parser" in summary_all
    assert summary_all["action_parser"]["count"] == 2.0
    assert summary_all["action_parser"]["p50_latency_ms"] == 100
    assert summary_all["action_parser"]["p95_latency_ms"] == 300
    assert summary_all["action_parser"]["parse_success_rate"] == 0.5

    assert "action_parser" in summary_sess_1
    assert "narration" not in summary_sess_1

import json

import pytest

from engine.llm_client import LLMClient, LLMParseError, LLMRequest, LLMTimeoutError


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_llm_client_logs_role_and_latency_metadata(tmp_path):
    log_path = tmp_path / "llm_performance.jsonl"

    client = LLMClient(
        transport=lambda request: {
            "text": '{"type":"query","parameters":{"question":"hello"}}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
        log_path=log_path,
    )

    request = LLMRequest(
        role="action_parser",
        system_prompt="system",
        user_message="hello",
        model="stub-model",
        max_tokens=128,
        temperature=0.0,
        metadata={"caller": "test"},
    )

    result = client.complete(request, parse_json=True)

    assert result["parsed"]["type"] == "query"
    records = _read_jsonl(log_path)
    assert len(records) == 1
    assert records[0]["role"] == "action_parser"
    assert records[0]["model"] == "stub-model"
    assert records[0]["latency_ms"] >= 0
    assert records[0]["metadata"]["caller"] == "test"


def test_llm_client_raises_parse_error_and_logs_failure(tmp_path):
    log_path = tmp_path / "llm_performance.jsonl"

    client = LLMClient(
        transport=lambda request: {
            "text": "not-json",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
        log_path=log_path,
    )

    request = LLMRequest(
        role="action_parser",
        system_prompt="system",
        user_message="hello",
        model="stub-model",
        max_tokens=128,
        temperature=0.0,
    )

    with pytest.raises(LLMParseError):
        client.complete(request, parse_json=True)

    records = _read_jsonl(log_path)
    assert len(records) == 1
    assert records[0]["parse_success"] is False
    assert records[0]["metadata"]["error"] == "parse"


def test_llm_client_raises_timeout_error_and_logs_failure(tmp_path):
    log_path = tmp_path / "llm_performance.jsonl"

    def _timeout_transport(_request):
        raise TimeoutError("timeout")

    client = LLMClient(transport=_timeout_transport, log_path=log_path)

    request = LLMRequest(
        role="narration",
        system_prompt="system",
        user_message="hello",
        model="stub-model",
        max_tokens=128,
        temperature=0.7,
    )

    with pytest.raises(LLMTimeoutError):
        client.complete(request, parse_json=False)

    records = _read_jsonl(log_path)
    assert len(records) == 1
    assert records[0]["role"] == "narration"
    assert records[0]["parse_success"] is False
    assert records[0]["metadata"]["error"] == "timeout"

from pathlib import Path

from tests.eval.run_eval import load_golden_actions, run_eval, write_eval_result


def _mock_parser(case):
    expected_type = case["expected_action_type"]
    expected_parameters = case.get("expected_parameters", {})
    return {
        "type": expected_type,
        "parameters": expected_parameters,
    }


def test_eval_runner_computes_accuracy_and_performance_metrics(tmp_path):
    data_path = Path("tests/eval/golden_actions.jsonl")
    cases = load_golden_actions(data_path)

    metrics = run_eval(cases, _mock_parser)

    assert metrics.total_cases == len(cases)
    assert metrics.action_type_accuracy == 1.0
    assert metrics.parameter_exact_match == 1.0
    assert metrics.parameter_partial_match == 1.0
    assert metrics.parse_success_rate == 1.0
    assert metrics.validation_pass_rate == 1.0
    assert metrics.avg_latency_ms >= 0
    assert metrics.p95_latency_ms >= 0

    output_file = tmp_path / "eval_results.jsonl"
    write_eval_result(metrics, output_file)
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8").strip()

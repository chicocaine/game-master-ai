from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_step(script_name: str) -> tuple[bool, str]:
    process = subprocess.run(
        [sys.executable, f"scripts/{script_name}"],
        text=True,
        capture_output=True,
        cwd=ROOT,
    )

    ok = process.returncode == 0
    output = (process.stdout or "") + (process.stderr or "")
    return ok, output.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run aggregated M5 CLI checks")
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional path to write machine-readable JSON results",
    )
    args = parser.parse_args()

    steps = [
        "cli_preflight.py",
        "cli_test_deterministic.py",
        "cli_test_live_smoke.py",
        "cli_test_pregame_gating.py",
        "cli_test_clarify_flow.py",
        "cli_test_enemy_turn.py",
    ]

    print("CLI Test Suite (M5)")
    failed: list[str] = []
    step_results: list[dict[str, object]] = []

    for step in steps:
        ok, output = _run_step(step)
        status = "PASS" if ok else "FAIL"
        print(f"\n[{status}] {step}")
        if output:
            print(output)
        if not ok:
            failed.append(step)
        step_results.append(
            {
                "script": step,
                "passed": ok,
                "status": status,
                "output": output,
            }
        )

    print("\nSummary")
    print(f"- total: {len(steps)}")
    print(f"- passed: {len(steps) - len(failed)}")
    print(f"- failed: {len(failed)}")

    if args.json_out:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": len(steps),
            "passed": len(steps) - len(failed),
            "failed": len(failed),
            "failed_steps": failed,
            "results": step_results,
        }
        out_path = Path(args.json_out)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"- json_report: {out_path}")

    if failed:
        print(f"- failed_steps: {', '.join(failed)}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

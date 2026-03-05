from __future__ import annotations

import subprocess
import sys
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

    for step in steps:
        ok, output = _run_step(step)
        status = "PASS" if ok else "FAIL"
        print(f"\n[{status}] {step}")
        if output:
            print(output)
        if not ok:
            failed.append(step)

    print("\nSummary")
    print(f"- total: {len(steps)}")
    print(f"- passed: {len(steps) - len(failed)}")
    print(f"- failed: {len(failed)}")

    if failed:
        print(f"- failed_steps: {', '.join(failed)}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

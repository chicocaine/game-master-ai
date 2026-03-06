from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    prompts = [
        "what can i do right now?",
        "what state am i currently in?",
        "what actions are legal in this state?",
        "how do i create a player?",
        "how do i choose a dungeon?",
        "what do i need before starting?",
        "exit",
    ]

    process = subprocess.run(
        [sys.executable, "main.py", "--live-llm"],
        input="\n".join(prompts) + "\n",
        text=True,
        capture_output=True,
        cwd=ROOT,
    )

    debug_turn_count = process.stdout.count("[debug][turn]")

    print("Live CLI Extended Test")
    print(f"- return_code: {process.returncode}")
    print(f"- started_cli: {'Game Master AI CLI' in process.stdout}")
    print(f"- mode_line_present: {'live LLM enabled' in process.stdout or 'falling back' in process.stdout}")
    print(f"- debug_turn_count: {debug_turn_count}")

    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)
        raise SystemExit(process.returncode)

    if debug_turn_count < 6:
        print(process.stdout)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

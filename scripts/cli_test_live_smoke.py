from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    process = subprocess.run(
        [sys.executable, "main.py", "--live-llm"],
        input="what can i do right now?\nexit\n",
        text=True,
        capture_output=True,
        cwd=Path(__file__).resolve().parents[1],
    )

    print("Live CLI Smoke Test")
    print(f"- return_code: {process.returncode}")
    print(f"- started_cli: {'Game Master AI CLI' in process.stdout}")
    print(f"- mode_line_present: {'live LLM enabled' in process.stdout or 'falling back' in process.stdout}")

    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)
        raise SystemExit(process.returncode)


if __name__ == "__main__":
    main()

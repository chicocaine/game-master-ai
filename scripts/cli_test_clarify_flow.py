from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _latest_turn_log() -> Path | None:
    paths = sorted((ROOT / "logs/sessions").glob("sess_*_turns.jsonl"), key=lambda p: p.stat().st_mtime)
    return paths[-1] if paths else None


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    clarify_payload = {
        "type": "clarify",
        "ambiguous_field": "scope",
        "question": "What scope do you mean?",
        "options": [
            {"label": "Rules", "value": "rules"},
            {"label": "State", "value": "state"},
        ],
        "action_template": {
            "type": "query",
            "parameters": {"question": "what can i do right now?"},
        },
    }

    scripted_inputs = [
        json.dumps(clarify_payload),
        "2",
        "exit",
    ]

    before = _latest_turn_log()
    process = subprocess.run(
        [sys.executable, "main.py"],
        input="\n".join(scripted_inputs) + "\n",
        text=True,
        capture_output=True,
        cwd=ROOT,
    )
    after = _latest_turn_log()

    if process.returncode != 0 or after is None or (before is not None and after == before):
        print(process.stdout)
        print(process.stderr)
        raise SystemExit(1)

    rows = _read_jsonl(after)
    if len(rows) < 2:
        raise SystemExit(1)

    first, second = rows[-2], rows[-1]
    first_is_clarify_no_advance = first.get("advanced_turn") is False and first.get("clarify") is not None
    second_advances_turn = second.get("advanced_turn") is True and second.get("clarify") is None
    second_is_query = isinstance(second.get("parsed", {}), dict) and second["parsed"].get("type") == "query"

    print("Clarify Flow CLI Test")
    print(f"- return_code: {process.returncode}")
    print(f"- first_turn_clarify_no_advance: {first_is_clarify_no_advance}")
    print(f"- second_turn_advanced: {second_advances_turn}")
    print(f"- second_turn_query_action: {second_is_query}")

    if not (first_is_clarify_no_advance and second_advances_turn and second_is_query):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

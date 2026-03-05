from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.state_manager import EngineStateManager


def _latest_turn_log() -> Path | None:
    paths = sorted((ROOT / "logs/sessions").glob("sess_*_turns.jsonl"), key=lambda p: p.stat().st_mtime)
    return paths[-1] if paths else None


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    manager = EngineStateManager("data")
    session = manager.create_session()

    player_template = next(iter(session.player_templates.values()))
    dungeon_template = next(iter(session.dungeon_templates.values()))

    create_payload = {
        "type": "create_player",
        "parameters": {
            "name": player_template.name,
            "description": player_template.description,
            "race": player_template.race.id,
            "archetype": player_template.archetype.id,
            "weapons": [weapon.id for weapon in player_template.weapons],
            "player_instance_id": "plr_inst_cli_gate_01",
        },
    }

    scripted_inputs = [
        json.dumps({"type": "start", "parameters": {}}),
        json.dumps(create_payload),
        json.dumps({"type": "remove_player", "parameters": {"player_instance_id": "plr_inst_cli_gate_01"}}),
        json.dumps(create_payload),
        json.dumps({"type": "choose_dungeon", "parameters": {"dungeon_id": dungeon_template.id}}),
        json.dumps({"type": "start", "parameters": {}}),
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
    has_rejected_start = any(
        row.get("parsed", {}).get("type") == "start" and row.get("validation_failed") is True
        for row in rows
        if isinstance(row.get("parsed", {}), dict)
    )
    has_remove_player = any(
        row.get("parsed", {}).get("type") == "remove_player"
        for row in rows
        if isinstance(row.get("parsed", {}), dict)
    )
    has_successful_start = any(
        row.get("parsed", {}).get("type") == "start" and row.get("advanced_turn") is True and row.get("validation_failed") is False
        for row in rows
        if isinstance(row.get("parsed", {}), dict)
    )

    print("Pregame Gating CLI Test")
    print(f"- return_code: {process.returncode}")
    print(f"- rejected_start_without_setup: {has_rejected_start}")
    print(f"- remove_player_flow_seen: {has_remove_player}")
    print(f"- successful_start_after_setup: {has_successful_start}")

    if not (has_rejected_start and has_remove_player and has_successful_start):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

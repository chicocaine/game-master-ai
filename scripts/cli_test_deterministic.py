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
    paths = sorted(Path("logs/sessions").glob("sess_*_turns.jsonl"), key=lambda p: p.stat().st_mtime)
    return paths[-1] if paths else None


def main() -> None:
    manager = EngineStateManager("data")
    session = manager.create_session()

    player_template = next(iter(session.player_templates.values()))
    dungeon_template = next(iter(session.dungeon_templates.values()))

    scripted_inputs = [
        json.dumps(
            {
                "type": "create_player",
                "parameters": {
                    "name": player_template.name,
                    "description": player_template.description,
                    "race": player_template.race.id,
                    "archetype": player_template.archetype.id,
                    "weapons": [weapon.id for weapon in player_template.weapons],
                    "player_instance_id": "plr_inst_cli_test_01",
                },
            }
        ),
        json.dumps({"type": "choose_dungeon", "parameters": {"dungeon_id": dungeon_template.id}}),
        json.dumps({"type": "start", "parameters": {}}),
        "what can i do right now?",
        "exit",
    ]

    before = _latest_turn_log()
    process = subprocess.run(
        [sys.executable, "main.py"],
        input="\n".join(scripted_inputs) + "\n",
        text=True,
        capture_output=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    after = _latest_turn_log()

    print("Deterministic CLI Test")
    print(f"- return_code: {process.returncode}")
    print(f"- started_cli: {'Game Master AI CLI' in process.stdout}")
    print(f"- produced_turn_log: {after is not None and (before is None or after != before)}")

    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)
        raise SystemExit(process.returncode)


if __name__ == "__main__":
    main()

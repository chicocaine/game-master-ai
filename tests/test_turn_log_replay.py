import json

from engine.game_loop import GameLoop
from engine.runtime_logger import RuntimeTurnLogger
from engine.state_manager import EngineStateManager
from util.turn_log_replay import replay_turn_log


def test_replay_turn_log_replays_actionable_records(tmp_path):
    manager = EngineStateManager("data")

    session_log = manager.create_session()
    runtime_logger = RuntimeTurnLogger("sess_replay_case", log_dir=tmp_path)

    player_template = next(iter(session_log.player_templates.values()))
    payload = {
        "type": "create_player",
        "parameters": {
            "name": player_template.name,
            "description": player_template.description,
            "race": player_template.race.id,
            "archetype": player_template.archetype.id,
            "weapons": [weapon.id for weapon in player_template.weapons],
            "player_instance_id": "plr_inst_replay_01",
        },
    }

    loop = GameLoop(
        parser=lambda _raw, _session: payload,
        runtime_logger=runtime_logger,
    )
    loop.run_turn(session_log, "create")

    replay_session = manager.create_session()
    summary = replay_turn_log(runtime_logger.path, replay_session, strict_event_check=True)

    assert summary.total_records == 1
    assert summary.actionable_records == 1
    assert summary.replayed_records == 1
    assert summary.skipped_records == 0
    assert summary.mismatched_turns == 0
    assert summary.mismatched_event_sets == 0
    assert len(replay_session.party) == 1
    assert replay_session.party[0].player_instance_id == "plr_inst_replay_01"


def test_replay_turn_log_skips_non_actionable_records(tmp_path):
    path = tmp_path / "sess_skip_turns.jsonl"
    row = {
        "parsed": {"type": "clarify", "question": "Who?"},
        "turn_before": 0,
        "turn_after": 0,
        "parser_failed": False,
        "events": [],
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    session = EngineStateManager("data").create_session()
    summary = replay_turn_log(path, session)

    assert summary.total_records == 1
    assert summary.actionable_records == 0
    assert summary.replayed_records == 0
    assert summary.mismatched_turns == 0

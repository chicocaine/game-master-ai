import json
from pathlib import Path

import pytest

from core.enums import EventType, GameState
from core.events import create_event
from util import logger as logger_module
from util.logger import ErrorLogger, EventLogger, SessionLogger


@pytest.fixture(autouse=True)
def log_dirs(tmp_path, monkeypatch):
	events_dir = tmp_path / "events"
	sessions_dir = tmp_path / "sessions"
	errors_dir = tmp_path / "errors"

	monkeypatch.setattr(logger_module, "_EVENTS_DIR", events_dir)
	monkeypatch.setattr(logger_module, "_SESSIONS_DIR", sessions_dir)
	monkeypatch.setattr(logger_module, "_ERRORS_DIR", errors_dir)
	monkeypatch.setattr(ErrorLogger, "_GLOBAL_PATH", errors_dir / "errors.jsonl")

	return {"events": events_dir, "sessions": sessions_dir, "errors": errors_dir}


def _read_jsonl(path: Path) -> list:
	return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _read_json(path: Path) -> dict:
	return json.loads(path.read_text(encoding="utf-8"))


# EventLogger
def test_event_logger_creates_session_jsonl_on_first_log(log_dirs):
	el = EventLogger("sess_001")
	el.log(create_event(EventType.GAME_STARTED, "game_started"))

	assert el.path.exists()
	assert el.path.name == "sess_001.jsonl"


def test_event_logger_record_contains_all_event_fields(log_dirs):
	el = EventLogger("sess_002")
	event = create_event(
		EventType.ROOM_ENTERED,
		"room_entered",
		payload={"room_id": "room_01"},
		source="engine",
	)
	el.log(event)

	rec = _read_jsonl(el.path)[0]
	assert rec["event_id"] == event.event_id
	assert rec["type"] == EventType.ROOM_ENTERED.value
	assert rec["name"] == "room_entered"
	assert rec["payload"]["room_id"] == "room_01"
	assert rec["source"] == "engine"
	assert "timestamp" in rec


def test_event_logger_record_includes_session_id(log_dirs):
	el = EventLogger("sess_003")
	el.log(create_event(EventType.TURN_STARTED, "turn_started"))

	rec = _read_jsonl(el.path)[0]
	assert rec["session_id"] == "sess_003"


def test_event_logger_log_many_appends_all_events(log_dirs):
	el = EventLogger("sess_004")
	events = [
		create_event(EventType.ROUND_STARTED, "round_started"),
		create_event(EventType.ATTACK_HIT, "attack_hit", {"damage": 5}),
		create_event(EventType.DEATH, "death", {"entity_id": "enm_01"}),
	]
	el.log_many(events)

	records = _read_jsonl(el.path)
	assert len(records) == 3
	assert records[0]["type"] == EventType.ROUND_STARTED.value
	assert records[2]["type"] == EventType.DEATH.value


def test_event_logger_successive_logs_append_not_overwrite(log_dirs):
	el = EventLogger("sess_005")
	el.log(create_event(EventType.TURN_STARTED, "turn_started"))
	el.log(create_event(EventType.TURN_ENDED, "turn_ended"))

	assert len(_read_jsonl(el.path)) == 2


def test_event_logger_separate_sessions_write_to_separate_files(log_dirs):
	el_a = EventLogger("sess_a")
	el_b = EventLogger("sess_b")
	el_a.log(create_event(EventType.GAME_STARTED, "game_started"))
	el_b.log(create_event(EventType.GAME_FINISHED, "game_finished"))

	assert el_a.path != el_b.path
	assert _read_jsonl(el_a.path)[0]["type"] == EventType.GAME_STARTED.value
	assert _read_jsonl(el_b.path)[0]["type"] == EventType.GAME_FINISHED.value


def test_event_logger_path_property_points_to_correct_file(log_dirs):
	el = EventLogger("sess_path")
	assert el.path == log_dirs["events"] / "sess_path.jsonl"


# SessionLogger
def test_session_logger_creates_json_file_on_init(log_dirs):
	sl = SessionLogger("s_init")

	assert sl.path.exists()
	assert sl.path.name == "s_init.json"


def test_session_logger_initial_file_contains_correct_session_id(log_dirs):
	sl = SessionLogger("s_id_check")

	assert _read_json(sl.path)["session_id"] == "s_id_check"


def test_session_logger_auto_generates_session_id_when_none_given(log_dirs):
	sl = SessionLogger()

	assert sl.session_id
	assert sl.path.exists()


def test_session_logger_set_dungeon_persists_to_file(log_dirs):
	sl = SessionLogger("s_dng")
	sl.set_dungeon("dng_01", "The Sunken Catacombs")

	data = _read_json(sl.path)
	assert data["dungeon_id"] == "dng_01"
	assert data["dungeon_name"] == "The Sunken Catacombs"


def test_session_logger_set_party_persists_to_file(log_dirs):
	sl = SessionLogger("s_party")
	sl.set_party([{"instance_id": "plr_inst_01", "name": "Araniel", "hp": 24}])

	data = _read_json(sl.path)
	assert len(data["party"]) == 1
	assert data["party"][0]["name"] == "Araniel"


def test_session_logger_state_transition_appends_to_history(log_dirs):
	sl = SessionLogger("s_trans")
	sl.log_state_transition(GameState.PREGAME, GameState.EXPLORATION, reason="start")
	sl.log_state_transition(GameState.EXPLORATION, GameState.ENCOUNTER, reason="enemy triggered")

	history = _read_json(sl.path)["state_history"]
	assert len(history) == 2
	assert history[0]["from"] == "pregame"
	assert history[0]["to"] == "exploration"
	assert history[0]["reason"] == "start"
	assert history[1]["from"] == "exploration"
	assert history[1]["to"] == "encounter"


def test_session_logger_state_transition_record_includes_timestamp(log_dirs):
	sl = SessionLogger("s_ts")
	sl.log_state_transition(GameState.PREGAME, GameState.EXPLORATION)

	entry = _read_json(sl.path)["state_history"][0]
	assert "timestamp" in entry
	assert entry["timestamp"]


def test_session_logger_update_stats_merges_into_summary_stats(log_dirs):
	sl = SessionLogger("s_stats")
	sl.update_stats({"rooms_cleared": 2})
	sl.update_stats({"enemies_defeated": 5, "rooms_cleared": 3})

	stats = _read_json(sl.path)["summary_stats"]
	assert stats["rooms_cleared"] == 3
	assert stats["enemies_defeated"] == 5


def test_session_logger_end_session_sets_outcome_and_ended_at(log_dirs):
	sl = SessionLogger("s_end")
	sl.end_session("victory", summary_stats={"damage_dealt": 88})

	data = _read_json(sl.path)
	assert data["outcome"] == "victory"
	assert data["ended_at"] is not None
	assert data["summary_stats"]["damage_dealt"] == 88


def test_session_logger_end_session_merges_metadata(log_dirs):
	sl = SessionLogger("s_meta")
	sl.end_session("abandoned", metadata={"reason": "player quit"})

	assert _read_json(sl.path)["metadata"]["reason"] == "player quit"


def test_session_logger_update_metadata_persists_to_file(log_dirs):
	sl = SessionLogger("s_updmeta")
	sl.update_metadata({"model": "gpt-4o-mini"})

	assert _read_json(sl.path)["metadata"]["model"] == "gpt-4o-mini"


def test_session_logger_file_is_rewritten_on_each_mutation(log_dirs):
	sl = SessionLogger("s_flush")
	sl.set_dungeon("dng_01", "Crypt")
	assert _read_json(sl.path)["dungeon_id"] == "dng_01"

	sl.set_party([{"name": "Brynn"}])
	assert _read_json(sl.path)["party"][0]["name"] == "Brynn"


def test_session_logger_record_property_reflects_in_memory_state(log_dirs):
	sl = SessionLogger("s_rec")
	sl.set_dungeon("dng_x", "X Dungeon")

	assert sl.record.dungeon_id == "dng_x"
	assert sl.record.dungeon_name == "X Dungeon"


def test_session_logger_path_property_points_to_correct_file(log_dirs):
	sl = SessionLogger("s_pathprop")
	assert sl.path == log_dirs["sessions"] / "s_pathprop.json"


# ErrorLogger
def test_error_logger_log_writes_to_global_errors_file(log_dirs):
	err = ErrorLogger()
	err.log("something went wrong", error_type="test_error")

	records = _read_jsonl(log_dirs["errors"] / "errors.jsonl")
	assert len(records) == 1
	assert records[0]["message"] == "something went wrong"
	assert records[0]["error_type"] == "test_error"


def test_error_logger_log_also_writes_to_session_file_when_session_id_given(log_dirs):
	err = ErrorLogger("e_sess_01")
	err.log("session error")

	session_path = log_dirs["errors"] / "e_sess_01.jsonl"
	assert session_path.exists()
	rec = _read_jsonl(session_path)[0]
	assert rec["message"] == "session error"
	assert rec["session_id"] == "e_sess_01"


def test_error_logger_no_session_id_skips_session_file(log_dirs):
	err = ErrorLogger()
	err.log("no session")

	assert err.session_path is None
	jsonl_files = list((log_dirs["errors"]).glob("*.jsonl"))
	assert all(f.name == "errors.jsonl" for f in jsonl_files)


def test_error_logger_record_contains_required_fields(log_dirs):
	err = ErrorLogger("e_fields")
	err.log("check fields", error_type="validation_error", context={"phase": "test"})

	rec = _read_jsonl(log_dirs["errors"] / "errors.jsonl")[0]
	assert "error_id" in rec
	assert "timestamp" in rec
	assert rec["error_type"] == "validation_error"
	assert rec["context"]["phase"] == "test"
	assert rec["traceback"] is None


def test_error_logger_each_record_gets_unique_error_id(log_dirs):
	err = ErrorLogger("e_uuid")
	err.log("first")
	err.log("second")

	records = _read_jsonl(log_dirs["errors"] / "errors.jsonl")
	assert records[0]["error_id"] != records[1]["error_id"]


def test_error_logger_log_exc_captures_traceback_and_exception_type(log_dirs):
	err = ErrorLogger("e_exc")
	try:
		raise ValueError("boom")
	except ValueError as exc:
		err.log_exc(exc, context={"phase": "test_exc"})

	rec = _read_jsonl(log_dirs["errors"] / "errors.jsonl")[0]
	assert rec["message"] == "boom"
	assert rec["error_type"] == "exception"
	assert "ValueError" in rec["traceback"]


def test_error_logger_log_exc_uses_custom_message_when_provided(log_dirs):
	err = ErrorLogger("e_custmsg")
	try:
		raise RuntimeError("internal")
	except RuntimeError as exc:
		err.log_exc(exc, message="custom message", error_type="runtime_error")

	rec = _read_jsonl(log_dirs["errors"] / "errors.jsonl")[0]
	assert rec["message"] == "custom message"
	assert rec["error_type"] == "runtime_error"


def test_error_logger_errors_from_multiple_sessions_aggregate_in_global_log(log_dirs):
	ErrorLogger("e_multi_a").log("error from A")
	ErrorLogger("e_multi_b").log("error from B")

	messages = [r["message"] for r in _read_jsonl(log_dirs["errors"] / "errors.jsonl")]
	assert "error from A" in messages
	assert "error from B" in messages


def test_error_logger_global_path_property(log_dirs):
	err = ErrorLogger()
	assert err.global_path == log_dirs["errors"] / "errors.jsonl"


def test_error_logger_session_path_property_when_session_id_given(log_dirs):
	err = ErrorLogger("e_pathprop")
	assert err.session_path == log_dirs["errors"] / "e_pathprop.jsonl"


def test_error_logger_session_path_property_is_none_without_session_id(log_dirs):
	err = ErrorLogger()
	assert err.session_path is None

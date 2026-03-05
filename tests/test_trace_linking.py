from agent.agent_manager import AgentManager
from engine.game_loop import GameLoop
from engine.runtime_logger import RuntimeTurnLogger
from engine.state_manager import EngineStateManager


def test_runtime_log_includes_trace_id_for_turn(tmp_path):
    session = EngineStateManager("data").create_session()
    logger = RuntimeTurnLogger("sess_trace_test", log_dir=tmp_path)
    manager = AgentManager()
    loop = GameLoop(parser=manager.parse_player_input, runtime_logger=logger)

    loop.run_turn(session, "what can I do right now?")

    content = logger.path.read_text(encoding="utf-8")
    assert '"trace_id":' in content


def test_agent_llm_metadata_includes_trace_and_session_id():
    captured = {}

    def _json_completion(role, system_prompt, user_message, metadata):
        captured.update(metadata)
        return {"type": "query", "parameters": {"question": "ok"}}

    session = EngineStateManager("data").create_session()
    setattr(session, "_active_trace_id", "trace_123")
    setattr(session, "_session_id", "sess_abc")

    manager = AgentManager(json_completion=_json_completion)
    manager.parse_player_input("what can i do", session)

    assert captured["trace_id"] == "trace_123"
    assert captured["session_id"] == "sess_abc"
    assert captured["role"] == "action_parser"

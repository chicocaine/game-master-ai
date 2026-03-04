import json

from core.enums import ActionType, DifficultyType, GameState
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from core.registry.enemy_registry import load_enemy_model_registry
from core.states.session import GameSessionState
from engine.game_loop import GameLoop
from engine.runtime_logger import RuntimeTurnLogger
from engine.state_manager import EngineStateManager


def _build_enemy_turn_session() -> tuple[GameSessionState, str, str]:
    manager = EngineStateManager("data")
    session = manager.create_session()

    player_template = next(iter(session.player_templates.values()))
    player = player_template
    player.player_instance_id = "plr_inst_runtime_enemy_target"
    session.party = [player]

    enemy_template = next(iter(load_enemy_model_registry("data").values()))
    enemy = Enemy.from_dict(enemy_template.to_dict())
    enemy.enemy_instance_id = "enm_inst_runtime_01"

    room = Room(
        id="room_runtime_enemy",
        name="Runtime Enemy Room",
        description="room",
        is_visited=True,
        is_cleared=False,
        is_rested=False,
        connections=[],
        encounters=[
            Encounter(
                id="enc_runtime_enemy_01",
                name="Runtime Enemy Encounter",
                description="enc",
                difficulty=DifficultyType.EASY,
                cleared=False,
                clear_reward=1,
                enemies=[enemy],
            )
        ],
        allowed_rests=[],
    )
    session.dungeon = Dungeon(
        id="dgn_runtime_enemy",
        name="Runtime Enemy Dungeon",
        description="dgn",
        difficulty=DifficultyType.EASY,
        start_room=room.id,
        end_room=room.id,
        rooms=[room],
    )
    session.dungeon_id = session.dungeon.id
    session.state = GameState.ENCOUNTER
    session.exploration.current_room_id = room.id
    session.encounter.active_encounter_id = "enc_runtime_enemy_01"
    session.encounter.turn_order = [enemy.enemy_instance_id, player.player_instance_id]
    session.encounter.current_turn_index = 0

    return session, enemy.enemy_instance_id, player.player_instance_id


def test_engine_state_manager_creates_session_with_templates():
    manager = EngineStateManager("data")

    session = manager.create_session()

    assert isinstance(session, GameSessionState)
    assert session.state == GameState.PREGAME
    assert len(session.player_templates) > 0
    assert len(session.dungeon_templates) > 0


def test_engine_state_manager_reset_preserves_template_catalog():
    manager = EngineStateManager("data")
    session = manager.create_session()

    session.party = [next(iter(session.player_templates.values()))]
    session.dungeon_id = next(iter(session.dungeon_templates.keys()))
    session.turn = 5

    manager.reset_session(session)

    assert session.state == GameState.PREGAME
    assert session.party == []
    assert session.dungeon_id == ""
    assert session.turn == 0
    assert len(session.player_templates) > 0
    assert len(session.dungeon_templates) > 0


def test_game_loop_clarify_does_not_advance_turn_or_mutate_state():
    manager = EngineStateManager("data")
    session = manager.create_session()

    loop = GameLoop(
        parser=lambda _raw, _session: {
            "type": "clarify",
            "ambiguous_field": "target_instance_ids",
            "question": "Who do you want to target?",
            "options": [
                {"label": "Enemy A", "value": "enm_inst_01"},
                {"label": "Enemy B", "value": "enm_inst_02"},
            ],
        }
    )

    result = loop.run_turn(session, "attack the skeleton")

    assert result.advanced_turn is False
    assert result.clarify is not None
    assert result.events == []
    assert session.turn == 0
    assert session.state == GameState.PREGAME


def test_game_loop_applies_action_dict_through_core_pipeline():
    manager = EngineStateManager("data")
    session = manager.create_session()
    player_template = next(iter(session.player_templates.values()))

    payload = {
        "type": ActionType.CREATE_PLAYER.value,
        "parameters": {
            "name": player_template.name,
            "description": player_template.description,
            "race": player_template.race.id,
            "archetype": player_template.archetype.id,
            "weapons": [weapon.id for weapon in player_template.weapons],
            "player_instance_id": "plr_inst_runtime_01",
        },
    }

    loop = GameLoop(parser=lambda _raw, _session: payload)
    result = loop.run_turn(session, "create my character")

    assert result.advanced_turn is True
    assert len(result.events) > 0
    assert len(session.party) == 1
    assert session.party[0].player_instance_id == "plr_inst_runtime_01"


def test_game_loop_pending_clarify_resolves_selected_option_to_action():
    manager = EngineStateManager("data")
    session = manager.create_session()

    loop = GameLoop(
        parser=lambda _raw, _session: {
            "type": "clarify",
            "ambiguous_field": "scope",
            "question": "What scope do you mean?",
            "options": [
                {"label": "Rules", "value": "rules"},
                {"label": "State", "value": "state"},
            ],
            "action_template": {
                "type": "query",
                "parameters": {"question": "what can I do?"},
            },
        }
    )

    first = loop.run_turn(session, "query")
    second = loop.run_turn(session, "2")

    assert first.advanced_turn is False
    assert first.clarify is not None
    assert first.events == []

    assert second.advanced_turn is True
    assert second.clarify is None
    assert any(event.name == "action_resolved" for event in second.events)


def test_game_loop_run_enemy_turn_executes_selector_action():
    session, enemy_id, _player_id = _build_enemy_turn_session()
    loop = GameLoop(parser=lambda _raw, _session: {"type": "query", "parameters": {"question": "noop"}})

    result = loop.run_enemy_turn(
        session,
        selector=lambda _session, actor_id: {
            "type": "end_turn",
            "actor_instance_id": actor_id,
            "parameters": {},
        },
    )

    assert result.advanced_turn is True
    assert any(event.name == "turn_ended" for event in result.events)


def test_game_loop_run_enemy_turn_falls_back_and_logs_rejection_on_selector_error():
    session, enemy_id, _player_id = _build_enemy_turn_session()
    loop = GameLoop(parser=lambda _raw, _session: {"type": "query", "parameters": {"question": "noop"}})

    result = loop.run_enemy_turn(
        session,
        selector=lambda _session, _actor_id: (_ for _ in ()).throw(RuntimeError("selector failure")),
    )

    assert result.advanced_turn is True
    assert any(event.type.value == "action_rejected" for event in result.events)
    assert any(event.name == "turn_ended" for event in result.events)


def test_game_loop_runtime_logger_marks_parser_failures(tmp_path):
    session = EngineStateManager("data").create_session()
    runtime_logger = RuntimeTurnLogger("sess_parser_fail", log_dir=tmp_path)
    loop = GameLoop(
        parser=lambda _raw, _session: (_ for _ in ()).throw(ValueError("parse boom")),
        runtime_logger=runtime_logger,
    )

    result = loop.run_turn(session, "invalid")

    assert result.advanced_turn is False
    records = [json.loads(line) for line in runtime_logger.path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["parser_failed"] is True
    assert records[0]["validation_failed"] is False


def test_game_loop_runtime_logger_marks_validation_failures(tmp_path):
    session = EngineStateManager("data").create_session()
    runtime_logger = RuntimeTurnLogger("sess_validation_fail", log_dir=tmp_path)
    loop = GameLoop(
        parser=lambda _raw, _session: {"type": "create_player", "parameters": {}},
        runtime_logger=runtime_logger,
    )

    result = loop.run_turn(session, "create")

    assert result.advanced_turn is False
    records = [json.loads(line) for line in runtime_logger.path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["parser_failed"] is False
    assert records[0]["validation_failed"] is True

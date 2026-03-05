from agent.context_builder import build_state_context
from engine.state_manager import EngineStateManager


def test_context_builder_includes_legal_actions_and_dungeon_state():
    session = EngineStateManager("data").create_session()

    context = build_state_context(session)

    assert context["state"] == "pregame"
    assert "legal_actions" in context
    assert "create_player" in context["legal_actions"]
    assert "query" in context["legal_actions"]
    assert "current_room" in context
    assert context["dungeon"]["selected"] is False


def test_context_builder_party_rows_include_status_and_defense_fields():
    manager = EngineStateManager("data")
    session = manager.create_session()

    player = next(iter(session.player_templates.values()))
    player.player_instance_id = "plr_inst_ctx_01"
    session.party = [player]

    context = build_state_context(session)
    assert len(context["party"]) == 1
    row = context["party"][0]
    assert "status_effects" in row
    assert "resistances" in row
    assert "immunities" in row
    assert "vulnerabilities" in row


def test_context_builder_pregame_includes_party_build_and_dungeon_options():
    session = EngineStateManager("data").create_session()

    context = build_state_context(session)
    pregame = context["pregame"]
    build_options = pregame["build_options"]

    assert pregame["active"] is True
    assert isinstance(build_options["races"], list) and len(build_options["races"]) > 0
    assert isinstance(build_options["archetypes"], list) and len(build_options["archetypes"]) > 0
    assert isinstance(build_options["weapons"], list) and len(build_options["weapons"]) > 0
    assert isinstance(build_options["player_templates"], list) and len(build_options["player_templates"]) > 0
    assert isinstance(build_options["dungeons"], list) and len(build_options["dungeons"]) > 0
    assert pregame["start_readiness"]["can_start"] is False
    assert len(pregame["start_readiness"]["missing_requirements"]) >= 1


def test_context_builder_pregame_start_readiness_updates_when_party_and_dungeon_selected():
    session = EngineStateManager("data").create_session()
    player_template = next(iter(session.player_templates.values()))
    dungeon_template = next(iter(session.dungeon_templates.values()))

    player_template.player_instance_id = "plr_inst_pregame_ctx_01"
    session.party = [player_template]
    session.dungeon = dungeon_template
    session.dungeon_id = dungeon_template.id

    context = build_state_context(session)
    readiness = context["pregame"]["start_readiness"]

    assert readiness["can_start"] is True
    assert readiness["missing_requirements"] == []

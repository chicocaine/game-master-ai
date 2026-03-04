import json

from agent.agent_manager import AgentManager
from core.enums import ActionType, DifficultyType, GameState
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from engine.game_loop import GameLoop
from engine.state_manager import EngineStateManager


def test_agent_parser_returns_clarify_for_empty_input():
    manager = AgentManager()
    session = EngineStateManager("data").create_session()

    result = manager.parse_player_input("   ", session)

    assert result["type"] == "clarify"
    assert result["ambiguous_field"] == "input"


def test_agent_manager_parsed_action_runs_through_game_loop():
    manager = AgentManager()
    session = EngineStateManager("data").create_session()
    player_template = next(iter(session.player_templates.values()))

    payload = {
        "type": ActionType.CREATE_PLAYER.value,
        "parameters": {
            "name": player_template.name,
            "description": player_template.description,
            "race": player_template.race.id,
            "archetype": player_template.archetype.id,
            "weapons": [weapon.id for weapon in player_template.weapons],
            "player_instance_id": "plr_inst_agent_01",
        },
        "metadata": {"source": "test"},
    }

    loop = GameLoop(parser=manager.parse_player_input, narrator=manager.narrate_events)
    result = loop.run_turn(session, json.dumps(payload))

    assert result.advanced_turn is True
    assert result.clarify is None
    assert len(session.party) == 1
    assert session.party[0].player_instance_id == "plr_inst_agent_01"
    assert result.narration


def test_agent_parser_fallbacks_to_query_action_for_free_text():
    manager = AgentManager()
    session = EngineStateManager("data").create_session()
    loop = GameLoop(parser=manager.parse_player_input)

    result = loop.run_turn(session, "what can I do right now?")

    assert result.advanced_turn is True
    assert any(event.name == "action_resolved" for event in result.events)


def test_enemy_ai_returns_attack_payload_when_encounter_has_targets():
    manager = AgentManager()
    state_manager = EngineStateManager("data")
    session = state_manager.create_session()

    player = next(iter(session.player_templates.values()))
    player.player_instance_id = "plr_inst_enemy_target"
    session.party = [player]

    enemy_template = next(iter(session.player_templates.values()))
    enemy = Enemy(
        id=enemy_template.id,
        name=enemy_template.name,
        description=enemy_template.description,
        race=enemy_template.race,
        archetype=enemy_template.archetype,
        hp=enemy_template.hp,
        max_hp=enemy_template.max_hp,
        base_AC=enemy_template.base_AC,
        AC=enemy_template.AC,
        spell_slots=enemy_template.spell_slots,
        max_spell_slots=enemy_template.max_spell_slots,
        initiative_mod=enemy_template.initiative_mod,
        active_status_effects=list(enemy_template.active_status_effects),
        weapons=list(enemy_template.weapons),
        known_attacks=list(enemy_template.known_attacks),
        known_spells=list(enemy_template.known_spells),
        resistances=list(enemy_template.resistances),
        immunities=list(enemy_template.immunities),
        vulnerabilities=list(enemy_template.vulnerabilities),
        enemy_instance_id="enm_inst_agent_01",
        persona="aggressive",
    )

    room = Room(
        id="room_agent",
        name="Agent Room",
        description="room",
        is_visited=True,
        is_cleared=False,
        is_rested=False,
        connections=[],
        encounters=[
            Encounter(
                id="enc_agent_01",
                name="Agent Encounter",
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
        id="dgn_agent",
        name="Agent Dungeon",
        description="dgn",
        difficulty=DifficultyType.EASY,
        start_room=room.id,
        end_room=room.id,
        rooms=[room],
    )
    session.dungeon_id = session.dungeon.id
    session.state = GameState.ENCOUNTER
    session.exploration.current_room_id = room.id
    session.encounter.active_encounter_id = "enc_agent_01"
    session.encounter.turn_order = [enemy.enemy_instance_id, player.player_instance_id]
    session.encounter.current_turn_index = 0

    payload = manager.choose_enemy_action(session, enemy.enemy_instance_id)

    assert payload["type"] in {"attack", "end_turn"}
    assert payload["actor_instance_id"] == enemy.enemy_instance_id
    if payload["type"] == "attack":
        assert payload["parameters"]["target_instance_ids"] == [player.player_instance_id]


def test_agent_attack_clarify_then_selection_resolves_to_attack_action():
    manager = AgentManager()
    state_manager = EngineStateManager("data")
    session = state_manager.create_session()

    player = next(iter(session.player_templates.values()))
    player.player_instance_id = "plr_inst_clarify_01"
    session.party = [player]

    enemy_template = next(iter(session.player_templates.values()))
    enemy_one = Enemy(
        id=enemy_template.id,
        name=enemy_template.name,
        description=enemy_template.description,
        race=enemy_template.race,
        archetype=enemy_template.archetype,
        hp=enemy_template.hp,
        max_hp=enemy_template.max_hp,
        base_AC=enemy_template.base_AC,
        AC=enemy_template.AC,
        spell_slots=enemy_template.spell_slots,
        max_spell_slots=enemy_template.max_spell_slots,
        initiative_mod=enemy_template.initiative_mod,
        active_status_effects=list(enemy_template.active_status_effects),
        weapons=list(enemy_template.weapons),
        known_attacks=list(enemy_template.known_attacks),
        known_spells=list(enemy_template.known_spells),
        resistances=list(enemy_template.resistances),
        immunities=list(enemy_template.immunities),
        vulnerabilities=list(enemy_template.vulnerabilities),
        enemy_instance_id="enm_inst_clarify_01",
        persona="aggressive",
    )
    enemy_two = Enemy.from_dict(enemy_one.to_dict())
    enemy_two.enemy_instance_id = "enm_inst_clarify_02"

    room = Room(
        id="room_clarify",
        name="Clarify Room",
        description="room",
        is_visited=True,
        is_cleared=False,
        is_rested=False,
        connections=[],
        encounters=[
            Encounter(
                id="enc_clarify_01",
                name="Clarify Encounter",
                description="enc",
                difficulty=DifficultyType.EASY,
                cleared=False,
                clear_reward=1,
                enemies=[enemy_one, enemy_two],
            )
        ],
        allowed_rests=[],
    )
    session.dungeon = Dungeon(
        id="dgn_clarify",
        name="Clarify Dungeon",
        description="dgn",
        difficulty=DifficultyType.EASY,
        start_room=room.id,
        end_room=room.id,
        rooms=[room],
    )
    session.dungeon_id = session.dungeon.id
    session.state = GameState.ENCOUNTER
    session.exploration.current_room_id = room.id
    session.encounter.active_encounter_id = "enc_clarify_01"
    session.encounter.turn_order = [player.player_instance_id, enemy_one.enemy_instance_id, enemy_two.enemy_instance_id]
    session.encounter.current_turn_index = 0

    loop = GameLoop(parser=manager.parse_player_input)

    first = loop.run_turn(session, "attack")
    second = loop.run_turn(session, "2")

    assert first.advanced_turn is False
    assert first.clarify is not None
    assert first.clarify["ambiguous_field"] == "target_instance_ids"
    assert len(first.clarify["options"]) == 2

    assert second.advanced_turn is True
    assert second.clarify is None
    assert any(event.name == "attack_declared" for event in second.events)

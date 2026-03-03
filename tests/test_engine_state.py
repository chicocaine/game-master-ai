from core.actions import create_action
from core.enums import ActionType, DifficultyType, GameState, RestType
from engine.game_state import GameSessionState, apply_action
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from core.registry.enemy_registry import load_enemy_model_registry
from core.registry.player_registry import load_player_registry


def _build_simple_dungeon() -> Dungeon:
    return Dungeon(
        id="dgn_test_simple",
        name="Simple Dungeon",
        description="Two connected rooms",
        difficulty=DifficultyType.EASY,
        start_room="room_start",
        end_room="room_end",
        rooms=[
            Room(
                id="room_start",
                name="Start Room",
                description="A safe start room",
                is_visited=False,
                is_cleared=True,
                is_rested=False,
                connections=["room_end"],
                encounters=[],
                allowed_rests=[RestType.SHORT, RestType.LONG],
            ),
            Room(
                id="room_end",
                name="End Room",
                description="The final room",
                is_visited=False,
                is_cleared=True,
                is_rested=False,
                connections=["room_start"],
                encounters=[],
                allowed_rests=[RestType.SHORT],
            ),
        ],
    )


def _build_encounter_dungeon(enemy_template: Enemy) -> Dungeon:
    enemy = Enemy.from_dict(enemy_template.to_dict())
    enemy.hp = 1
    enemy.max_hp = 1

    return Dungeon(
        id="dgn_test_encounter",
        name="Encounter Dungeon",
        description="Single room with one fight",
        difficulty=DifficultyType.EASY,
        start_room="room_fight",
        end_room="room_fight",
        rooms=[
            Room(
                id="room_fight",
                name="Fight Room",
                description="An arena",
                is_visited=False,
                is_cleared=False,
                is_rested=False,
                connections=[],
                encounters=[
                    Encounter(
                        id="enc_test_01",
                        name="Test Encounter",
                        description="One weak enemy",
                        difficulty=DifficultyType.EASY,
                        cleared=False,
                        clear_reward=1,
                        enemies=[enemy],
                    )
                ],
                allowed_rests=[],
            )
        ],
    )


def _build_session() -> GameSessionState:
    player_templates = load_player_registry("data")
    player_id = next(iter(player_templates.keys()))
    return GameSessionState(player_templates=player_templates, dungeon_templates={"dgn_test_simple": _build_simple_dungeon()}), player_id


def _create_player_action_params_from_template(player_template) -> dict:
    return {
        "name": player_template.name,
        "description": player_template.description,
        "race": player_template.race.id,
        "archetype": player_template.archetype.id,
        "weapons": [weapon.id for weapon in player_template.weapons],
        "player_instance_id": "plr_inst_01",
    }


def test_pregame_to_exploration_move_and_rest_flow():
    session, player_id = _build_session()
    player_template = session.player_templates[player_id]

    apply_action(session, create_action(ActionType.CREATE_PLAYER, _create_player_action_params_from_template(player_template)))
    apply_action(session, create_action(ActionType.CHOOSE_DUNGEON, {"dungeon_id": "dgn_test_simple"}))
    apply_action(session, create_action(ActionType.START))

    assert session.state == GameState.EXPLORATION
    assert session.exploration.current_room_id == "room_start"

    session.party[0].hp = max(1, session.party[0].hp - 3)
    apply_action(session, create_action(ActionType.REST, {"rest_type": "short"}))
    assert session.dungeon.rooms[0].is_rested is True

    move_events = apply_action(session, create_action(ActionType.MOVE, {"destination_room_id": "room_end"}))
    assert session.exploration.current_room_id == "room_end"
    assert all(event.type.value != "action_rejected" for event in move_events)


def test_move_rejected_for_unconnected_room():
    session, player_id = _build_session()
    player_template = session.player_templates[player_id]

    apply_action(session, create_action(ActionType.CREATE_PLAYER, _create_player_action_params_from_template(player_template)))
    apply_action(session, create_action(ActionType.CHOOSE_DUNGEON, {"dungeon_id": "dgn_test_simple"}))
    apply_action(session, create_action(ActionType.START))

    events = apply_action(session, create_action(ActionType.MOVE, {"destination_room_id": "room_missing"}))
    assert any(event.type.value == "action_rejected" for event in events)


def test_encounter_state_and_back_to_exploration_after_kill():
    player_templates = load_player_registry("data")
    player_id = next(iter(player_templates.keys()))
    enemy_templates = load_enemy_model_registry("data")
    enemy_template = next(iter(enemy_templates.values()))

    session = GameSessionState(
        player_templates=player_templates,
        dungeon_templates={"dgn_test_encounter": _build_encounter_dungeon(enemy_template)},
    )

    player_template = player_templates[player_id]

    apply_action(session, create_action(ActionType.CREATE_PLAYER, _create_player_action_params_from_template(player_template)))
    apply_action(session, create_action(ActionType.CHOOSE_DUNGEON, {"dungeon_id": "dgn_test_encounter"}))
    apply_action(session, create_action(ActionType.START))

    assert session.state == GameState.ENCOUNTER
    assert session.encounter.active_encounter_id == "enc_test_01"

    player_attack_id = session.party[0].merged_attacks[0].id

    attack = create_action(
        ActionType.ATTACK,
        {
            "attack_id": player_attack_id,
            "target_instance_ids": ["enc_test_01_enemy_1"],
        },
        actor_instance_id="plr_inst_01",
    )
    apply_action(session, attack)

    assert session.state in {GameState.EXPLORATION, GameState.POSTGAME}


def test_postgame_finish_resets_session_to_pregame():
    session, player_id = _build_session()
    player_template = session.player_templates[player_id]
    apply_action(session, create_action(ActionType.CREATE_PLAYER, _create_player_action_params_from_template(player_template)))
    apply_action(session, create_action(ActionType.CHOOSE_DUNGEON, {"dungeon_id": "dgn_test_simple"}))
    apply_action(session, create_action(ActionType.ABANDON))

    assert session.state == GameState.POSTGAME

    apply_action(session, create_action(ActionType.FINISH))

    assert session.state == GameState.PREGAME
    assert session.party == []
    assert session.dungeon is None
    assert session.dungeon_id == ""


def test_game_session_serialization_round_trip_preserves_state_payloads():
    session, player_id = _build_session()
    player_template = session.player_templates[player_id]
    apply_action(session, create_action(ActionType.CREATE_PLAYER, _create_player_action_params_from_template(player_template)))
    apply_action(session, create_action(ActionType.CHOOSE_DUNGEON, {"dungeon_id": "dgn_test_simple"}))
    apply_action(session, create_action(ActionType.START))
    apply_action(session, create_action(ActionType.EXPLORE))

    serialized = session.to_dict()
    restored = GameSessionState.from_dict(serialized)

    assert restored.state == session.state
    assert restored.exploration.current_room_id == session.exploration.current_room_id
    assert restored.turn == session.turn
    assert len(restored.party) == len(session.party)

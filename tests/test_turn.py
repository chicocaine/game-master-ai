from core.enums import DifficultyType, GameState, RestType, StatusEffectType
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from core.models.status_effect import StatusEffectDefinition, StatusEffectInstance
from core.registry.enemy_registry import load_enemy_model_registry
from core.registry.player_registry import load_player_registry
from core.resolution.turn import resolve_end_turn
from core.states.session import GameSessionState


def _build_turn_session() -> tuple[GameSessionState, str, str]:
    player_templates = load_player_registry("data")
    player = next(iter(player_templates.values()))
    player.player_instance_id = "plr_inst_01"

    enemy_templates = load_enemy_model_registry("data")
    enemy_template = next(iter(enemy_templates.values()))
    enemy = Enemy.from_dict(enemy_template.to_dict())
    enemy.enemy_instance_id = "enm_inst_01"

    encounter = Encounter(
        id="enc_turn_test",
        name="Turn Encounter",
        description="turn tests",
        difficulty=DifficultyType.EASY,
        cleared=False,
        clear_reward=1,
        enemies=[enemy],
    )
    room = Room(
        id="room_turn_test",
        name="Turn Room",
        description="turn room",
        is_visited=True,
        is_cleared=False,
        is_rested=False,
        connections=[],
        encounters=[encounter],
        allowed_rests=[RestType.SHORT],
    )
    dungeon = Dungeon(
        id="dgn_turn_test",
        name="Turn Dungeon",
        description="turn dungeon",
        difficulty=DifficultyType.EASY,
        start_room=room.id,
        end_room=room.id,
        rooms=[room],
    )

    session = GameSessionState(
        state=GameState.ENCOUNTER,
        party=[player],
        dungeon_id=dungeon.id,
        dungeon=dungeon,
    )
    session.exploration.current_room_id = room.id
    session.encounter.active_encounter_id = encounter.id
    session.encounter.turn_order = [player.player_instance_id, enemy.enemy_instance_id]
    session.encounter.current_turn_index = 0

    return session, player.player_instance_id, enemy.enemy_instance_id


def test_resolve_end_turn_skips_stunned_actor_and_ticks_effect():
    session, player_id, enemy_id = _build_turn_session()

    enemy = session.dungeon.rooms[0].encounters[0].enemies[0]
    enemy.active_status_effects.append(
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_stunned_turn",
                name="Stunned",
                description="skip turn",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "stunned"},
            ),
            duration=1,
        )
    )

    events = resolve_end_turn(session)

    skipped_events = [
        item
        for item in events
        if item.type.value == "turn_skipped"
        and item.payload.get("actor_instance_id") == enemy_id
    ]
    assert skipped_events
    assert skipped_events[0].payload.get("turn_skip_reason") == "stunned"
    assert enemy.active_status_effects == []
    assert session.encounter.turn_order[session.encounter.current_turn_index] == player_id
    assert all(
        not (item.type.value == "turn_started" and item.payload.get("actor_instance_id") == enemy_id)
        for item in events
    )


def test_resolve_end_turn_skips_asleep_actor():
    session, player_id, enemy_id = _build_turn_session()

    enemy = session.dungeon.rooms[0].encounters[0].enemies[0]
    enemy.active_status_effects.append(
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_asleep_turn",
                name="Asleep",
                description="skip turn",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "asleep"},
            ),
            duration=2,
        )
    )

    events = resolve_end_turn(session)

    skipped_events = [
        item
        for item in events
        if item.type.value == "turn_skipped"
        and item.payload.get("actor_instance_id") == enemy_id
    ]
    assert skipped_events
    assert skipped_events[0].payload.get("turn_skip_reason") == "asleep"
    assert session.encounter.turn_order[session.encounter.current_turn_index] == player_id
    assert all(
        not (item.type.value == "turn_started" and item.payload.get("actor_instance_id") == enemy_id)
        for item in events
    )

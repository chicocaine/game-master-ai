from core.enums import DifficultyType, GameState, StatusEffectType
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from core.models.status_effect import StatusEffectDefinition, StatusEffectInstance
from core.registry.enemy_registry import load_enemy_model_registry
from core.resolution.status_effects import (
    is_entity_asleep,
    is_entity_restrained,
    is_entity_silenced,
    is_entity_stunned,
    remove_negative_status_effects_from_actor,
    tick_status_effects_for_actor,
)
from core.states.session import GameSessionState


def _encounter_session_with_enemy() -> tuple[GameSessionState, Enemy]:
    enemy_templates = load_enemy_model_registry("data")
    enemy_template = next(iter(enemy_templates.values()))
    enemy = Enemy.from_dict(enemy_template.to_dict())
    enemy.enemy_instance_id = "enm_inst_01"
    enemy.hp = 20
    enemy.max_hp = 20

    encounter = Encounter(
        id="enc_test",
        name="Status Encounter",
        description="status test",
        difficulty=DifficultyType.EASY,
        cleared=False,
        clear_reward=1,
        enemies=[enemy],
    )
    room = Room(
        id="room_test",
        name="Status Room",
        description="status room",
        is_visited=True,
        is_cleared=False,
        is_rested=False,
        connections=[],
        encounters=[encounter],
        allowed_rests=[],
    )
    dungeon = Dungeon(
        id="dgn_status",
        name="Status Dungeon",
        description="status dungeon",
        difficulty=DifficultyType.EASY,
        start_room=room.id,
        end_room=room.id,
        rooms=[room],
    )

    session = GameSessionState(state=GameState.ENCOUNTER, dungeon=dungeon)
    session.exploration.current_room_id = room.id
    session.encounter.active_encounter_id = encounter.id
    session.encounter.turn_order = [enemy.enemy_instance_id]
    session.encounter.current_turn_index = 0
    return session, enemy


def test_tick_dot_and_hot_apply_values_and_remove_on_expire():
    session, enemy = _encounter_session_with_enemy()

    dot = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_dot_test",
            name="Burn",
            description="dot",
            type=StatusEffectType.DOT,
            parameters={"value": 4, "damage_type": "fire"},
        ),
        duration=1,
    )
    hot = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_hot_test",
            name="Regen",
            description="hot",
            type=StatusEffectType.HOT,
            parameters={"value": 3},
        ),
        duration=1,
    )

    enemy.hp = 10
    enemy.active_status_effects = [dot, hot]

    events = tick_status_effects_for_actor(session, enemy.enemy_instance_id)

    assert enemy.hp == 9
    assert enemy.active_status_effects == []
    assert any(item.type.value == "damage_applied" for item in events)
    assert any(item.type.value == "healing_applied" for item in events)


def test_remove_negative_status_effects_only():
    _, enemy = _encounter_session_with_enemy()
    dot = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_dot_test",
            name="Burn",
            description="dot",
            type=StatusEffectType.DOT,
            parameters={"value": 1, "damage_type": "fire"},
        ),
        duration=2,
    )
    control = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_ctrl_test",
            name="Stun",
            description="control",
            type=StatusEffectType.CONTROL,
            parameters={"control_type": "stunned"},
        ),
        duration=2,
    )
    vulnerable = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_vuln_test",
            name="Vulnerable",
            description="vuln",
            type=StatusEffectType.VULNERABLE,
            parameters={"damage_type": "fire"},
        ),
        duration=2,
    )
    hot = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_hot_test",
            name="Regen",
            description="hot",
            type=StatusEffectType.HOT,
            parameters={"value": 1},
        ),
        duration=2,
    )

    enemy.active_status_effects = [dot, control, vulnerable, hot]

    events = remove_negative_status_effects_from_actor(enemy, enemy.enemy_instance_id)

    assert [effect.id for effect in enemy.active_status_effects] == ["se_hot_test"]
    assert len([item for item in events if item.type.value == "status_effect_removed"]) == 3


def test_control_placeholders_detect_control_types():
    _, enemy = _encounter_session_with_enemy()
    enemy.active_status_effects = [
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_stun",
                name="Stun",
                description="control",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "stunned"},
            ),
            duration=1,
        ),
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_silence",
                name="Silence",
                description="control",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "silenced"},
            ),
            duration=1,
        ),
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_sleep",
                name="Sleep",
                description="control",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "asleep"},
            ),
            duration=1,
        ),
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_restrain",
                name="Restrain",
                description="control",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "restrained"},
            ),
            duration=1,
        ),
    ]

    assert is_entity_stunned(enemy) is True
    assert is_entity_silenced(enemy) is True
    assert is_entity_asleep(enemy) is True
    assert is_entity_restrained(enemy) is True

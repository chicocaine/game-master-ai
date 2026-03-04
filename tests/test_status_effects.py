from core.enums import DamageType, DifficultyType, GameState, StatusEffectType
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from core.models.status_effect import StatusEffectDefinition, StatusEffectInstance
from core.registry.enemy_registry import load_enemy_model_registry
from core.resolution.status_effects import (
    apply_status_effect_to_actor,
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
            parameters={"value": 4, "damage_type": DamageType.FORCE.value},
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


def test_tick_dot_respects_active_immunity_status_effect():
    session, enemy = _encounter_session_with_enemy()
    enemy.hp = 20

    enemy.active_status_effects = [
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_dot_fire",
                name="Burn",
                description="dot",
                type=StatusEffectType.DOT,
                parameters={"value": 7, "damage_type": DamageType.FIRE.value},
            ),
            duration=1,
        ),
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_immunity_fire",
                name="Fire Immunity",
                description="immune",
                type=StatusEffectType.IMMUNITY,
                parameters={"damage_type": DamageType.FIRE.value},
            ),
            duration=2,
        ),
    ]

    events = tick_status_effects_for_actor(session, enemy.enemy_instance_id)

    damage_event = next(item for item in events if item.type.value == "damage_applied")
    assert damage_event.payload["amount"] == 0
    assert enemy.hp == 20


def test_tick_dot_respects_active_vulnerability_status_effect():
    session, enemy = _encounter_session_with_enemy()
    enemy.hp = 20

    enemy.active_status_effects = [
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_dot_fire",
                name="Burn",
                description="dot",
                type=StatusEffectType.DOT,
                parameters={"value": 4, "damage_type": DamageType.FORCE.value},
            ),
            duration=1,
        ),
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_vulnerable_fire",
                name="Fire Vulnerable",
                description="vulnerable",
                type=StatusEffectType.VULNERABLE,
                parameters={"damage_type": DamageType.FORCE.value},
            ),
            duration=2,
        ),
    ]

    events = tick_status_effects_for_actor(session, enemy.enemy_instance_id)

    damage_event = next(item for item in events if item.type.value == "damage_applied")
    assert damage_event.payload["amount"] == 8
    assert enemy.hp == 12


def test_ac_modifier_overwrite_replaces_existing_effect_and_updates_ac():
    _, enemy = _encounter_session_with_enemy()
    base_ac = enemy.AC

    first = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_ac_mod_first",
            name="Stone Skin I",
            description="ac",
            type=StatusEffectType.ACMOD,
            parameters={"value": 2},
        ),
        duration=2,
    )
    second = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_ac_mod_second",
            name="Stone Skin II",
            description="ac",
            type=StatusEffectType.ACMOD,
            parameters={"value": 5},
        ),
        duration=2,
    )

    apply_status_effect_to_actor(enemy, enemy.enemy_instance_id, first)
    events = apply_status_effect_to_actor(enemy, enemy.enemy_instance_id, second)

    assert enemy.AC == base_ac + 5
    assert [effect.id for effect in enemy.active_status_effects if effect.status_effect.type == StatusEffectType.ACMOD] == ["se_ac_mod_second"]
    assert any(item.type.value == "status_effect_removed" for item in events)


def test_ac_modifier_reverts_on_expiration_tick():
    session, enemy = _encounter_session_with_enemy()
    base_ac = enemy.AC

    effect = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_ac_mod_expire",
            name="Stone Skin",
            description="ac",
            type=StatusEffectType.ACMOD,
            parameters={"value": 3},
        ),
        duration=1,
    )
    apply_status_effect_to_actor(enemy, enemy.enemy_instance_id, effect)

    tick_status_effects_for_actor(session, enemy.enemy_instance_id)

    assert enemy.AC == base_ac
    assert all(item.id != "se_ac_mod_expire" for item in enemy.active_status_effects)


def test_atk_modifier_overwrite_replaces_existing_effect_and_updates_bonus():
    _, enemy = _encounter_session_with_enemy()

    first = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_atk_mod_first",
            name="Battle Focus I",
            description="atk",
            type=StatusEffectType.ATKMOD,
            parameters={"value": 1},
        ),
        duration=2,
    )
    second = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_atk_mod_second",
            name="Battle Focus II",
            description="atk",
            type=StatusEffectType.ATKMOD,
            parameters={"value": 4},
        ),
        duration=2,
    )

    apply_status_effect_to_actor(enemy, enemy.enemy_instance_id, first)
    events = apply_status_effect_to_actor(enemy, enemy.enemy_instance_id, second)

    assert enemy.attack_modifier_bonus == 4
    assert [effect.id for effect in enemy.active_status_effects if effect.status_effect.type == StatusEffectType.ATKMOD] == ["se_atk_mod_second"]
    assert any(item.type.value == "status_effect_removed" for item in events)

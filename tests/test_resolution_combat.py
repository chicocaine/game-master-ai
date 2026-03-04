from core.actions import create_action
from core.dice import RollResult
from core.enums import ActionType, AttackType, DamageType, DifficultyType, GameState, RestType, SpellType, StatusEffectType
from core.models.attack import Attack
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from core.models.spell import Spell
from core.models.status_effect import StatusEffectDefinition, StatusEffectInstance
from core.registry.enemy_registry import load_enemy_model_registry
from core.registry.player_registry import load_player_registry
from core.resolution.combat import calculate_damage_multiplier, resolve_attack_action, resolve_cast_spell_action
from core.resolution.status_effects import apply_status_effect_to_actor
from core.states.session import GameSessionState


def _build_encounter_session() -> tuple[GameSessionState, Enemy]:
    player_templates = load_player_registry("data")
    player_template = next(iter(player_templates.values()))
    player = player_template
    player.player_instance_id = "plr_inst_01"

    enemy_templates = load_enemy_model_registry("data")
    enemy_template = next(iter(enemy_templates.values()))
    enemy = Enemy.from_dict(enemy_template.to_dict())
    enemy.enemy_instance_id = "enm_inst_01"
    enemy.hp = 20
    enemy.max_hp = 20

    encounter = Encounter(
        id="enc_test_01",
        name="Combat Resolution Encounter",
        description="Encounter used for combat resolution tests",
        difficulty=DifficultyType.EASY,
        cleared=False,
        clear_reward=1,
        enemies=[enemy],
    )

    room = Room(
        id="room_test",
        name="Test Room",
        description="A room for combat tests",
        is_visited=True,
        is_cleared=False,
        is_rested=False,
        connections=[],
        encounters=[encounter],
        allowed_rests=[RestType.SHORT],
    )

    dungeon = Dungeon(
        id="dgn_combat",
        name="Combat Dungeon",
        description="Dungeon used for combat tests",
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
    return session, enemy


def test_calculate_damage_multiplier_rules():
    assert calculate_damage_multiplier(DamageType.FIRE, [DamageType.FIRE], [], []) == 0.0
    assert calculate_damage_multiplier(DamageType.FIRE, [], [DamageType.FIRE], []) == 0.5
    assert calculate_damage_multiplier(DamageType.FIRE, [], [], [DamageType.FIRE]) == 2.0
    assert calculate_damage_multiplier(DamageType.FIRE, [], [DamageType.FIRE], [DamageType.FIRE]) == 1.0
    assert calculate_damage_multiplier(DamageType.FIRE, [], [], []) == 1.0


def test_resolve_attack_applies_resistance_multiplier(monkeypatch):
    session, enemy = _build_encounter_session()

    attack = Attack(
        id="atk_test_slash",
        name="Slash",
        description="test",
        type=AttackType.MELEE,
        parameters={"damage_types": [DamageType.SLASHING], "magnitude": "1d8+1", "hit_modifiers": 2, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_attacks.append(attack)
    enemy.resistances = [DamageType.SLASHING]

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 18)
    monkeypatch.setattr(
        "core.resolution.combat.roll_dice",
        lambda expr: RollResult(total=9, rolls=[8], modifier=1, expression=expr),
    )

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    damage_event = next(item for item in events if item.type.value == "damage_applied")
    assert damage_event.payload["amount"] == 4
    assert enemy.hp == 16


def test_resolve_attack_applies_active_status_effect_resistance_multiplier(monkeypatch):
    session, enemy = _build_encounter_session()

    attack = Attack(
        id="atk_test_fire_active_res",
        name="Fire Hit",
        description="test",
        type=AttackType.MELEE,
        parameters={"damage_types": [DamageType.FIRE], "magnitude": "1d8", "hit_modifiers": 2, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_attacks.append(attack)
    enemy.active_status_effects = [
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_res_fire_active",
                name="Active Fire Ward",
                description="active resistance",
                type=StatusEffectType.RESISTANCE,
                parameters={"damage_type": DamageType.FIRE.value},
            ),
            duration=2,
        )
    ]

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 18)
    monkeypatch.setattr(
        "core.resolution.combat.roll_dice",
        lambda expr: RollResult(total=8, rolls=[8], modifier=0, expression=expr),
    )

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    damage_event = next(item for item in events if item.type.value == "damage_applied")
    assert damage_event.payload["amount"] == 4
    assert enemy.hp == 16


def test_resolve_attack_uses_save_vs_dc_and_can_miss(monkeypatch):
    session, enemy = _build_encounter_session()

    attack = Attack(
        id="atk_test_save",
        name="Saving Throw Attack",
        description="test",
        type=AttackType.RANGED,
        parameters={"damage_types": [DamageType.FIRE], "magnitude": "1d6", "hit_modifiers": 0, "DC": 12, "applied_status_effects": []},
    )
    session.party[0].known_attacks.append(attack)

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 12)

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert any(item.type.value == "attack_missed" for item in events)
    assert all(item.type.value != "damage_applied" for item in events)
    assert enemy.hp == 20


def test_resolve_attack_applies_status_effects_on_hit(monkeypatch):
    session, enemy = _build_encounter_session()

    effect = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_test_dot",
            name="Burn",
            description="Burning",
            type=StatusEffectType.DOT,
            parameters={"value": 1},
        ),
        duration=2,
    )
    attack = Attack(
        id="atk_test_status",
        name="Burning Slash",
        description="test",
        type=AttackType.MELEE,
        parameters={
            "damage_types": [DamageType.SLASHING],
            "magnitude": "1d4",
            "hit_modifiers": 3,
            "DC": 0,
            "applied_status_effects": [effect],
        },
    )
    session.party[0].known_attacks.append(attack)

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 20)
    monkeypatch.setattr(
        "core.resolution.combat.roll_dice",
        lambda expr: RollResult(total=3, rolls=[3], modifier=0, expression=expr),
    )

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert any(item.type.value == "status_effect_applied" for item in events)
    assert any(item.id == "se_test_dot" for item in enemy.active_status_effects)


def test_attack_modifier_status_effect_increases_attack_roll(monkeypatch):
    session, enemy = _build_encounter_session()

    attack = Attack(
        id="atk_test_attack_mod_status",
        name="Status Boosted Attack",
        description="test",
        type=AttackType.MELEE,
        parameters={"damage_types": [DamageType.SLASHING], "magnitude": "1d4", "hit_modifiers": 0, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_attacks.append(attack)
    apply_status_effect_to_actor(
        session.party[0],
        session.party[0].player_instance_id,
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_atk_mod_buff",
                name="Battle Focus",
                description="attack up",
                type=StatusEffectType.ATKMOD,
                parameters={"value": 3},
            ),
            duration=2,
        ),
    )
    enemy.AC = 13

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 10)
    monkeypatch.setattr(
        "core.resolution.combat.roll_dice",
        lambda expr: RollResult(total=3, rolls=[3], modifier=0, expression=expr),
    )

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    dice_event = next(item for item in events if item.type.value == "dice_rolled")
    assert dice_event.payload["status_effect_hit_modifiers"] == 3
    assert dice_event.payload["total_hit_modifiers"] == 3
    assert any(item.type.value == "attack_hit" for item in events)


def test_ac_modifier_status_effect_increases_target_ac(monkeypatch):
    session, enemy = _build_encounter_session()

    attack = Attack(
        id="atk_test_target_ac_mod",
        name="Against AC Buff",
        description="test",
        type=AttackType.MELEE,
        parameters={"damage_types": [DamageType.SLASHING], "magnitude": "1d4", "hit_modifiers": 2, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_attacks.append(attack)
    enemy.AC = 12
    enemy.base_AC = 12
    apply_status_effect_to_actor(
        enemy,
        enemy.enemy_instance_id,
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ac_mod_buff",
                name="Stone Skin",
                description="ac up",
                type=StatusEffectType.ACMOD,
                parameters={"value": 2},
            ),
            duration=2,
        ),
    )

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 10)

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    dice_event = next(item for item in events if item.type.value == "dice_rolled")
    assert dice_event.payload["target_base_ac"] == 12
    assert dice_event.payload["target_ac"] == 14
    assert any(item.type.value == "attack_missed" for item in events)
    assert all(item.type.value != "damage_applied" for item in events)


def test_single_target_attack_rejects_multiple_targets():
    session, enemy = _build_encounter_session()

    attack = Attack(
        id="atk_test_single_target",
        name="Single Target",
        description="test",
        type=AttackType.MELEE,
        parameters={"damage_types": [DamageType.SLASHING], "magnitude": "1d4", "hit_modifiers": 0, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_attacks.append(attack)

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id, "enm_inst_02"]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert len(events) == 1
    assert events[0].type.value == "action_rejected"


def test_aoe_attack_applies_to_multiple_targets(monkeypatch):
    session, enemy = _build_encounter_session()
    enemy_two = Enemy.from_dict(enemy.to_dict())
    enemy_two.enemy_instance_id = "enm_inst_02"
    session.dungeon.rooms[0].encounters[0].enemies.append(enemy_two)

    attack = Attack(
        id="atk_test_aoe",
        name="AOE Strike",
        description="test",
        type=AttackType.AOE_MELEE,
        parameters={"damage_types": [DamageType.FORCE], "magnitude": "1d4", "hit_modifiers": 5, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_attacks.append(attack)

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 20)
    monkeypatch.setattr(
        "core.resolution.combat.roll_dice",
        lambda expr: RollResult(total=2, rolls=[2], modifier=0, expression=expr),
    )

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id, enemy_two.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    damage_events = [item for item in events if item.type.value == "damage_applied"]
    assert len(damage_events) == 2
    assert enemy.hp == 18
    assert enemy_two.hp == 18


def test_heal_spell_restores_hp_and_spends_slots(monkeypatch):
    session, _ = _build_encounter_session()
    target = session.party[0]
    target.hp = 5

    spell = Spell(
        id="spl_test_heal",
        name="Test Heal",
        description="test",
        type=SpellType.HEAL,
        spell_cost=1,
        parameters={"magnitude": "1d8+2", "damage_types": [], "hit_modifiers": 0, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_spells.append(spell)
    starting_slots = session.party[0].spell_slots

    monkeypatch.setattr(
        "core.resolution.combat.roll_dice",
        lambda expr: RollResult(total=6, rolls=[4], modifier=2, expression=expr),
    )

    action = create_action(
        ActionType.CAST_SPELL,
        {"spell_id": spell.id, "target_instance_ids": [target.player_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_cast_spell_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert target.hp == 11
    assert session.party[0].spell_slots == starting_slots - 1
    assert any(item.type.value == "healing_applied" for item in events)
    mana_event = next(item for item in events if item.type.value == "mana_updated")
    assert mana_event.payload["spell_slots"] == session.party[0].spell_slots
    assert mana_event.payload["mana"] == session.party[0].spell_slots


def test_attack_spell_uses_save_vs_dc_and_can_miss(monkeypatch):
    session, enemy = _build_encounter_session()

    spell = Spell(
        id="spl_test_attack_dc",
        name="Test Attack DC",
        description="test",
        type=SpellType.ATTACK,
        spell_cost=1,
        parameters={"magnitude": "1d10", "damage_types": [DamageType.FIRE], "hit_modifiers": 0, "DC": 12, "applied_status_effects": []},
    )
    session.party[0].known_spells.append(spell)

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 12)

    action = create_action(
        ActionType.CAST_SPELL,
        {"spell_id": spell.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_cast_spell_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert any(item.type.value == "attack_missed" for item in events)
    assert all(item.type.value != "damage_applied" for item in events)
    assert enemy.hp == 20


def test_aoe_control_spell_applies_status_to_multiple_targets(monkeypatch):
    session, enemy = _build_encounter_session()
    enemy_two = Enemy.from_dict(enemy.to_dict())
    enemy_two.enemy_instance_id = "enm_inst_02"
    session.dungeon.rooms[0].encounters[0].enemies.append(enemy_two)

    control_effect = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_test_stun",
            name="Stun",
            description="stun",
            type=StatusEffectType.CONTROL,
            parameters={},
        ),
        duration=1,
    )
    spell = Spell(
        id="spl_test_aoe_control",
        name="Test AOE Control",
        description="test",
        type=SpellType.AOE_CONTROL,
        spell_cost=2,
        parameters={"magnitude": "1d6", "damage_types": [DamageType.THUNDER], "hit_modifiers": 0, "DC": 14, "applied_status_effects": [control_effect]},
    )
    session.party[0].known_spells.append(spell)

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 5)
    monkeypatch.setattr(
        "core.resolution.combat.roll_dice",
        lambda expr: RollResult(total=3, rolls=[3], modifier=0, expression=expr),
    )

    action = create_action(
        ActionType.CAST_SPELL,
        {"spell_id": spell.id, "target_instance_ids": [enemy.enemy_instance_id, enemy_two.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_cast_spell_action(session, session.dungeon.rooms[0].encounters[0], action)

    status_events = [item for item in events if item.type.value == "status_effect_applied"]
    assert len(status_events) == 2
    assert any(effect.id == "se_test_stun" for effect in enemy.active_status_effects)
    assert any(effect.id == "se_test_stun" for effect in enemy_two.active_status_effects)


def test_cleanse_spell_removes_matching_status_effects():
    session, enemy = _build_encounter_session()

    dot_effect = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_dot_fire_01",
            name="Burn",
            description="burn",
            type=StatusEffectType.DOT,
            parameters={"value": 1},
        ),
        duration=3,
    )
    hot_effect = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_hot_01",
            name="Regen",
            description="regen",
            type=StatusEffectType.HOT,
            parameters={"value": 1},
        ),
        duration=2,
    )
    enemy.active_status_effects = [dot_effect, hot_effect]

    cleanse_ref = StatusEffectInstance(
        status_effect=StatusEffectDefinition(
            id="se_dot_fire_01",
            name="Burn",
            description="burn",
            type=StatusEffectType.DOT,
            parameters={"value": 1},
        ),
        duration=0,
    )
    spell = Spell(
        id="spl_test_cleanse",
        name="Test Cleanse",
        description="test",
        type=SpellType.CLEANSE,
        spell_cost=1,
        parameters={"magnitude": "0d1", "damage_types": [], "hit_modifiers": 0, "DC": 0, "applied_status_effects": [cleanse_ref]},
    )
    session.party[0].known_spells.append(spell)

    action = create_action(
        ActionType.CAST_SPELL,
        {"spell_id": spell.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_cast_spell_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert [effect.id for effect in enemy.active_status_effects] == ["se_hot_01"]
    removed = [item for item in events if item.type.value == "status_effect_removed"]
    assert len(removed) == 1


def test_single_target_spell_rejects_multiple_targets():
    session, enemy = _build_encounter_session()

    spell = Spell(
        id="spl_test_single_target",
        name="Single Target Spell",
        description="test",
        type=SpellType.HEAL,
        spell_cost=1,
        parameters={"magnitude": "1d4", "damage_types": [], "hit_modifiers": 0, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_spells.append(spell)

    action = create_action(
        ActionType.CAST_SPELL,
        {"spell_id": spell.id, "target_instance_ids": [enemy.enemy_instance_id, "enm_inst_02"]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_cast_spell_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert len(events) == 1
    assert events[0].type.value == "action_rejected"


def test_attack_rejected_when_actor_is_stunned():
    session, enemy = _build_encounter_session()

    attack = Attack(
        id="atk_test_stun_block",
        name="Blocked Attack",
        description="test",
        type=AttackType.MELEE,
        parameters={"damage_types": [DamageType.SLASHING], "magnitude": "1d4", "hit_modifiers": 0, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_attacks.append(attack)
    session.party[0].active_status_effects = [
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_block_attack",
                name="Stunned",
                description="control",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "stunned"},
            ),
            duration=1,
        )
    ]

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert len(events) == 1
    assert events[0].type.value == "action_rejected"
    assert "Actor is stunned" in events[0].payload["errors"]


def test_cast_spell_rejected_when_actor_is_silenced():
    session, enemy = _build_encounter_session()

    spell = Spell(
        id="spl_test_silence_block",
        name="Blocked Spell",
        description="test",
        type=SpellType.ATTACK,
        spell_cost=1,
        parameters={"magnitude": "1d6", "damage_types": [DamageType.FIRE], "hit_modifiers": 0, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_spells.append(spell)
    session.party[0].active_status_effects = [
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_block_spell",
                name="Silenced",
                description="control",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "silenced"},
            ),
            duration=1,
        )
    ]

    action = create_action(
        ActionType.CAST_SPELL,
        {"spell_id": spell.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_cast_spell_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert len(events) == 1
    assert events[0].type.value == "action_rejected"
    assert "Actor is silenced" in events[0].payload["errors"]


def test_silenced_actor_can_still_attack(monkeypatch):
    session, enemy = _build_encounter_session()

    attack = Attack(
        id="atk_test_silenced_can_attack",
        name="Allowed Attack",
        description="test",
        type=AttackType.MELEE,
        parameters={"damage_types": [DamageType.SLASHING], "magnitude": "1d4", "hit_modifiers": 2, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_attacks.append(attack)
    session.party[0].active_status_effects = [
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_silenced_attack_ok",
                name="Silenced",
                description="control",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "silenced"},
            ),
            duration=1,
        )
    ]

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 20)
    monkeypatch.setattr(
        "core.resolution.combat.roll_dice",
        lambda expr: RollResult(total=3, rolls=[3], modifier=0, expression=expr),
    )

    action = create_action(
        ActionType.ATTACK,
        {"attack_id": attack.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_attack_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert all(item.type.value != "action_rejected" for item in events)
    assert any(item.type.value == "damage_applied" for item in events)


def test_restrained_actor_can_still_cast_spell(monkeypatch):
    session, enemy = _build_encounter_session()

    spell = Spell(
        id="spl_test_restrained_can_cast",
        name="Allowed Spell",
        description="test",
        type=SpellType.ATTACK,
        spell_cost=1,
        parameters={"magnitude": "1d6", "damage_types": [DamageType.FIRE], "hit_modifiers": 0, "DC": 0, "applied_status_effects": []},
    )
    session.party[0].known_spells.append(spell)
    session.party[0].active_status_effects = [
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_restrained_spell_ok",
                name="Restrained",
                description="control",
                type=StatusEffectType.CONTROL,
                parameters={"control_type": "restrained"},
            ),
            duration=1,
        )
    ]

    monkeypatch.setattr("core.resolution.combat.roll_d20", lambda: 20)
    monkeypatch.setattr(
        "core.resolution.combat.roll_dice",
        lambda expr: RollResult(total=4, rolls=[4], modifier=0, expression=expr),
    )

    action = create_action(
        ActionType.CAST_SPELL,
        {"spell_id": spell.id, "target_instance_ids": [enemy.enemy_instance_id]},
        actor_instance_id=session.party[0].player_instance_id,
    )
    events = resolve_cast_spell_action(session, session.dungeon.rooms[0].encounters[0], action)

    assert all(item.type.value != "action_rejected" for item in events)
    assert any(item.type.value == "damage_applied" for item in events)

from core.actions import create_action
from core.enums import ActionType, DifficultyType, GameState, RestType, SpellType
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from core.models.spell import Spell
from core.models.status_effect import StatusEffectDefinition, StatusEffectInstance
from core.registry.enemy_registry import load_enemy_model_registry
from core.registry.player_registry import load_player_registry
from core.states.manager import apply_action
from core.states.session import GameSessionState
from core.validation import validate_action_with_details


def _build_encounter_session() -> GameSessionState:
    player_templates = load_player_registry("data")
    player_template = next(iter(player_templates.values()))
    player = player_template
    player.player_instance_id = "plr_inst_01"

    enemy_templates = load_enemy_model_registry("data")
    enemy_template = next(iter(enemy_templates.values()))
    enemy = Enemy.from_dict(enemy_template.to_dict())
    enemy.enemy_instance_id = "enm_inst_01"

    encounter = Encounter(
        id="enc_test_01",
        name="Validation Encounter",
        description="Encounter used for validation tests",
        difficulty=DifficultyType.EASY,
        cleared=False,
        clear_reward=1,
        enemies=[enemy],
    )

    room = Room(
        id="room_test",
        name="Test Room",
        description="A room for validation tests",
        is_visited=True,
        is_cleared=False,
        is_rested=False,
        connections=[],
        encounters=[encounter],
        allowed_rests=[RestType.SHORT],
    )

    dungeon = Dungeon(
        id="dgn_validation",
        name="Validation Dungeon",
        description="Dungeon used for validation tests",
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
    return session


def test_validate_attack_rejects_unknown_attack_id():
    session = _build_encounter_session()

    action = create_action(
        ActionType.ATTACK,
        {
            "attack_id": "atk_missing_validation",
            "target_instance_ids": ["enm_inst_01"],
        },
        actor_instance_id="plr_inst_01",
    )

    result = validate_action_with_details(session, action)

    assert not result.is_valid
    assert any(issue.code == "unknown_attack" for issue in result.issues)


def test_validate_cast_spell_checks_spell_cost_affordability():
    session = _build_encounter_session()

    expensive_spell = Spell(
        id="spl_validation_expensive",
        name="Expensive Validation Spell",
        description="Spell used to validate slot affordability",
        type=SpellType.ATTACK,
        spell_cost=2,
        parameters={"magnitude": "1d4", "damage_types": [], "hit_modifiers": 0, "DC": 0},
    )
    session.party[0].known_spells.append(expensive_spell)
    session.party[0].spell_slots = 1

    action = create_action(
        ActionType.CAST_SPELL,
        {
            "spell_id": expensive_spell.id,
            "target_instance_ids": ["enm_inst_01"],
        },
        actor_instance_id="plr_inst_01",
    )

    result = validate_action_with_details(session, action)

    assert not result.is_valid
    issue = next(item for item in result.issues if item.code == "insufficient_spell_slots")
    assert issue.context["available_spell_slots"] == 1
    assert issue.context["required_spell_slots"] == 2


def test_apply_action_uses_validation_pipeline_for_unknown_attack():
    session = _build_encounter_session()

    action = create_action(
        ActionType.ATTACK,
        {
            "attack_id": "atk_missing_validation",
            "target_instance_ids": ["enm_inst_01"],
        },
        actor_instance_id="plr_inst_01",
    )

    events = apply_action(session, action)

    assert events[0].type.value == "action_rejected"
    assert "Unknown attack 'atk_missing_validation'" in events[0].payload["errors"]


def test_validate_create_player_rejects_missing_or_empty_weapons():
    session = GameSessionState(state=GameState.PREGAME)

    base_payload = {
        "name": "Araniel",
        "description": "A disciplined knight",
        "race": "human",
        "archetype": "warrior",
    }

    action_missing = create_action(ActionType.CREATE_PLAYER, dict(base_payload))
    result_missing = validate_action_with_details(session, action_missing)
    assert not result_missing.is_valid
    assert any(issue.code in {"invalid_weapons", "missing_weapons"} for issue in result_missing.issues)

    action_empty = create_action(ActionType.CREATE_PLAYER, {**base_payload, "weapons": []})
    result_empty = validate_action_with_details(session, action_empty)
    assert not result_empty.is_valid
    assert any(issue.code == "missing_weapons" for issue in result_empty.issues)

    action_invalid = create_action(ActionType.CREATE_PLAYER, {**base_payload, "weapons": ["   "]})
    result_invalid = validate_action_with_details(session, action_invalid)
    assert not result_invalid.is_valid
    assert any(issue.code == "invalid_weapon_id" for issue in result_invalid.issues)


def test_validate_attack_rejected_when_actor_restrained():
    session = _build_encounter_session()
    session.party[0].active_status_effects.append(
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_restrained_validation",
                name="Restrained",
                description="control",
                type="control",
                parameters={"control_type": "restrained"},
            ),
            duration=2,
        )
    )

    action = create_action(
        ActionType.ATTACK,
        {
            "attack_id": session.party[0].merged_attacks[0].id,
            "target_instance_ids": ["enm_inst_01"],
        },
        actor_instance_id="plr_inst_01",
    )

    result = validate_action_with_details(session, action)
    assert not result.is_valid
    assert any(issue.code == "actor_restrained" for issue in result.issues)


def test_validate_cast_spell_rejected_when_actor_silenced():
    session = _build_encounter_session()
    session.party[0].active_status_effects.append(
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_silenced_validation",
                name="Silenced",
                description="control",
                type="control",
                parameters={"control_type": "silenced"},
            ),
            duration=2,
        )
    )

    spell = Spell(
        id="spl_validation_basic",
        name="Validation Spell",
        description="spell",
        type=SpellType.ATTACK,
        spell_cost=1,
        parameters={"magnitude": "1d4", "damage_types": [], "hit_modifiers": 0, "DC": 0},
    )
    session.party[0].known_spells.append(spell)

    action = create_action(
        ActionType.CAST_SPELL,
        {
            "spell_id": spell.id,
            "target_instance_ids": ["enm_inst_01"],
        },
        actor_instance_id="plr_inst_01",
    )

    result = validate_action_with_details(session, action)
    assert not result.is_valid
    assert any(issue.code == "actor_silenced" for issue in result.issues)


def test_validate_cast_spell_allows_restrained_actor():
    session = _build_encounter_session()
    session.party[0].active_status_effects.append(
        StatusEffectInstance(
            status_effect=StatusEffectDefinition(
                id="se_ctrl_restrained_validation_spell",
                name="Restrained",
                description="control",
                type="control",
                parameters={"control_type": "restrained"},
            ),
            duration=2,
        )
    )

    spell = Spell(
        id="spl_validation_restrained_ok",
        name="Validation Spell",
        description="spell",
        type=SpellType.ATTACK,
        spell_cost=1,
        parameters={"magnitude": "1d4", "damage_types": [], "hit_modifiers": 0, "DC": 0},
    )
    session.party[0].known_spells.append(spell)

    action = create_action(
        ActionType.CAST_SPELL,
        {
            "spell_id": spell.id,
            "target_instance_ids": ["enm_inst_01"],
        },
        actor_instance_id="plr_inst_01",
    )

    result = validate_action_with_details(session, action)
    assert all(issue.code != "actor_restrained" for issue in result.issues)

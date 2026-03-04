from core.actions import Action, create_action, validate_action
from core.enums import ActionType


def test_converse_message_is_trimmed_on_from_dict():
	action = Action.from_dict(
		{
			"type": "converse",
			"parameters": {"message": "   hello there   "},
		}
	)

	assert action.parameters["message"] == "hello there"


def test_attack_requires_attack_id_and_target_instance_id():
	action = create_action(
		action_type=ActionType.ATTACK,
		parameters={"target_instance_ids": "enm_inst_01"},
	)

	errors = validate_action(action)

	assert "Missing required parameter 'attack_id' for action 'attack'" in errors


def test_attack_accepts_target_instance_id_as_string_or_list():
	action_single = create_action(
		action_type=ActionType.ATTACK,
		parameters={"attack_id": "atk_longsword_01", "target_instance_ids": "enm_inst_01"},
	)
	action_multi = create_action(
		action_type=ActionType.ATTACK,
		parameters={"attack_id": "atk_cleave_01", "target_instance_ids": ["enm_inst_01", "enm_inst_02"]},
	)

	assert validate_action(action_single) == []
	assert validate_action(action_multi) == []


def test_cast_spell_requires_target_instance_ids_and_rejects_blank():
	action_missing = create_action(
		action_type=ActionType.CAST_SPELL,
		parameters={"spell_id": "spl_fire_bolt_01"},
	)
	action_blank = create_action(
		action_type=ActionType.CAST_SPELL,
		parameters={"spell_id": "spl_fire_bolt_01", "target_instance_ids": "   "},
	)

	missing_errors = validate_action(action_missing)
	blank_errors = validate_action(action_blank)

	assert "Missing required parameter 'target_instance_ids' for action 'cast_spell'" in missing_errors
	assert "Parameter 'target_instance_ids' for action 'cast_spell' cannot be blank" in blank_errors


def test_cast_spell_accepts_target_instance_ids_string_or_list():
	action_single = create_action(
		action_type=ActionType.CAST_SPELL,
		parameters={"spell_id": "spl_fire_bolt_01", "target_instance_ids": "enm_inst_03"},
	)
	action_multi = create_action(
		action_type=ActionType.CAST_SPELL,
		parameters={"spell_id": "spl_chain_lightning_01", "target_instance_ids": ["enm_inst_03", "enm_inst_04"]},
	)

	assert validate_action(action_single) == []
	assert validate_action(action_multi) == []


def test_attack_legacy_target_instance_id_is_normalized():
	action = create_action(
		action_type=ActionType.ATTACK,
		parameters={"attack_id": "atk_longsword_01", "target_instance_id": "enm_inst_01"},
	)

	assert action.parameters["target_instance_ids"] == "enm_inst_01"
	assert validate_action(action) == []


def test_create_player_id_aliases_are_normalized():
	action = create_action(
		action_type=ActionType.CREATE_PLAYER,
		parameters={
			"name": "Araniel",
			"description": "A disciplined knight",
			"race_id": "human",
			"archetype_id": "warrior",
			"weapon_ids": ["wpn_longsword_01"],
		},
	)

	assert action.parameters["race"] == "human"
	assert action.parameters["archetype"] == "warrior"
	assert action.parameters["weapons"] == ["wpn_longsword_01"]
	assert validate_action(action) == []

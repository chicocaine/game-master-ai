from core.models.enemy import Enemy, create_enemy
from core.models.player import Player, create_player


def _weapon_dict(
	weapon_id: str,
	proficiency: str = "simple",
	handling: str = "one_handed",
	weight_class: str = "light",
	delivery: str = "melee",
	magic_type: str = "mundane",
):
	return {
		"id": weapon_id,
		"name": f"Weapon {weapon_id}",
		"description": "test weapon",
		"proficiency": proficiency,
		"handling": handling,
		"weight_class": weight_class,
		"delivery": delivery,
		"magic_type": magic_type,
		"known_attacks": [],
		"known_spells": [],
	}


def _base_entity_payload():
	return {
		"id": "ent_model_01",
		"name": "Model Entity",
		"description": "compat test",
		"race": {
			"id": "race_test_01",
			"name": "Test Race",
			"description": "race",
			"base_hp": 10,
			"base_AC": 11,
			"base_spell_slots": 1,
			"resistances": [],
			"immunities": [],
			"vulnerabilities": [],
			"archetype_constraints": [],
			"known_spells": [],
			"known_attacks": [],
		},
		"archetype": {
			"id": "arc_test_01",
			"name": "Test Archetype",
			"description": "archetype",
			"hp_mod": 2,
			"AC_mod": 1,
			"spell_slot_mod": 1,
			"resistances": [],
			"immunities": [],
			"vulnerabilities": [],
			"weapon_constraints": {
				"proficiency": [],
				"handling": [],
				"weight_class": [],
				"delivery": [],
				"magic_type": [],
			},
			"known_spells": [],
			"known_attacks": [],
			"weapons": [],
		},
		"weapons": [_weapon_dict("wpn_test_01")],
		"known_attacks": [],
		"known_spells": [],
		"resistances": [],
		"immunities": [],
		"vulnerabilities": [],
	}


def test_player_from_dict_round_trip_includes_instance_id():
	payload = _base_entity_payload()
	payload["player_instance_id"] = "plr_inst_01"

	player = Player.from_dict(payload)

	assert player.player_instance_id == "plr_inst_01"
	assert player.to_dict()["player_instance_id"] == "plr_inst_01"


def test_enemy_from_dict_round_trip_includes_instance_id():
	payload = _base_entity_payload()
	payload["enemy_instance_id"] = "enm_inst_01"

	enemy = Enemy.from_dict(payload)

	assert enemy.enemy_instance_id == "enm_inst_01"
	assert enemy.to_dict()["enemy_instance_id"] == "enm_inst_01"


def test_enemy_from_dict_round_trip_includes_persona():
	payload = _base_entity_payload()
	payload["persona"] = "cowardly, prefers ranged attacks"

	enemy = Enemy.from_dict(payload)

	assert enemy.persona == "cowardly, prefers ranged attacks"
	assert enemy.to_dict()["persona"] == "cowardly, prefers ranged attacks"


def test_enemy_from_dict_persona_defaults_to_empty_string_when_absent():
	payload = _base_entity_payload()

	enemy = Enemy.from_dict(payload)

	assert enemy.persona == ""
	assert enemy.to_dict()["persona"] == ""


def test_create_player_sets_player_instance_id_and_defaults():
	payload = _base_entity_payload()

	player = create_player(
		id=payload["id"],
		name=payload["name"],
		description=payload["description"],
		race=payload["race"],
		archetype=payload["archetype"],
		weapons=payload["weapons"],
		player_instance_id="plr_inst_create_01",
	)

	assert player.player_instance_id == "plr_inst_create_01"
	assert player.hp == 12
	assert player.AC == 12
	assert player.spell_slots == 2


def test_create_enemy_sets_enemy_instance_id_and_defaults():
	payload = _base_entity_payload()

	enemy = create_enemy(
		id=payload["id"],
		name=payload["name"],
		description=payload["description"],
		race=payload["race"],
		archetype=payload["archetype"],
		weapons=payload["weapons"],
		enemy_instance_id="enm_inst_create_01",
	)

	assert enemy.enemy_instance_id == "enm_inst_create_01"
	assert enemy.hp == 12
	assert enemy.AC == 12
	assert enemy.spell_slots == 2


def test_create_enemy_sets_persona():
	payload = _base_entity_payload()

	enemy = create_enemy(
		id=payload["id"],
		name=payload["name"],
		description=payload["description"],
		race=payload["race"],
		archetype=payload["archetype"],
		weapons=payload["weapons"],
		enemy_instance_id="enm_inst_create_02",
		persona="aggressive, charges front-liners first",
	)

	assert enemy.persona == "aggressive, charges front-liners first"
	assert enemy.to_dict()["persona"] == "aggressive, charges front-liners first"


def test_create_enemy_persona_defaults_to_empty_string():
	payload = _base_entity_payload()

	enemy = create_enemy(
		id=payload["id"],
		name=payload["name"],
		description=payload["description"],
		race=payload["race"],
		archetype=payload["archetype"],
		weapons=payload["weapons"],
		enemy_instance_id="enm_inst_create_03",
	)

	assert enemy.persona == ""

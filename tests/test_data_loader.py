import json
from pathlib import Path

import pytest

from core.registry.catalog_registry import load_catalog_registry
from core.registry.dungeon_registry import load_dungeon_registry
from core.registry.enemy_registry import load_enemy_registry
from core.registry.player_registry import load_player_registry
from util.entity_factory import (
    create_enemy_from_ids,
    create_entity_from_ids,
    create_player_from_ids,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def test_load_catalog_resolves_id_references():
    catalog = load_catalog_registry(DATA_DIR)

    fire_arrow = catalog.attacks["atk_fire_arrow_01"]
    assert [effect.id for effect in fire_arrow.applied_status_effects] == ["se_dot_fire_01"]
    assert fire_arrow.DC == 13

    heal_touch = catalog.spells["spl_heal_touch_01"]
    assert heal_touch.DC == 0

    staff = catalog.weapons["wpn_staff_01"]
    assert [spell.id for spell in staff.known_spells] == ["spl_fire_bolt_01", "spl_heal_touch_01"]

    race = catalog.races["race_human_01"]
    assert [attack.id for attack in race.known_attacks] == ["atk_longsword_01"]

    archetype = catalog.archetypes["arc_sage_01"]
    assert [weapon.id for weapon in archetype.weapons] == ["wpn_staff_01", "wpn_spellbow_01"]


def test_create_entity_from_ids_computes_defaults_and_merges():
    entity = create_entity_from_ids(
        entity_id="ent_test_01",
        name="Test Hero",
        description="Unit test entity",
        race_id="race_human_01",
        archetype_id="arc_warrior_01",
        weapon_ids=["wpn_longsword_01"],
        data_dir=DATA_DIR,
    )

    assert entity.hp == 16
    assert entity.AC == 13
    assert [weapon.id for weapon in entity.weapons] == ["wpn_longsword_01"]
    assert [attack.id for attack in entity.merged_attacks] == ["atk_longsword_01"]


def test_create_entity_from_ids_rejects_invalid_race_archetype_combo():
    with pytest.raises(ValueError, match="Archetype 'arc_warrior_01' is not allowed"):
        create_entity_from_ids(
            entity_id="ent_test_02",
            name="Invalid Combo",
            description="Should fail race/archetype validation",
            race_id="race_fireborn_01",
            archetype_id="arc_warrior_01",
            weapon_ids=["wpn_longsword_01"],
            data_dir=DATA_DIR,
        )


def test_create_entity_from_ids_rejects_invalid_weapon_constraints():
    with pytest.raises(ValueError, match="violates proficiency constraints"):
        create_entity_from_ids(
            entity_id="ent_test_03",
            name="Invalid Weapon",
            description="Should fail weapon constraints",
            race_id="race_human_01",
            archetype_id="arc_warrior_01",
            weapon_ids=["wpn_staff_01"],
            data_dir=DATA_DIR,
        )


def test_load_catalog_raises_on_unknown_reference(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    attacks = json.loads((data_copy / "attacks.json").read_text(encoding="utf-8"))
    attacks[1]["parameters"]["applied_status_effects"] = [["se_missing_999", 3]]
    (data_copy / "attacks.json").write_text(json.dumps(attacks, indent=2), encoding="utf-8")

    with pytest.raises(KeyError, match="se_missing_999"):
        load_catalog_registry(data_copy)


def test_create_player_from_ids_sets_instance_id_and_defaults():
    player = create_player_from_ids(
        entity_id="ent_player_test_01",
        name="Test Player",
        description="Unit test player",
        race_id="race_human_01",
        archetype_id="arc_warrior_01",
        weapon_ids=["wpn_longsword_01"],
        player_instance_id="player_inst_01",
        data_dir=DATA_DIR,
    )

    assert player.player_instance_id == "player_inst_01"
    assert player.hp == 16
    assert player.AC == 13
    assert player.initiative_mod == 1
    assert [weapon.id for weapon in player.weapons] == ["wpn_longsword_01"]


def test_create_enemy_from_ids_sets_instance_id_and_defaults():
    enemy = create_enemy_from_ids(
        entity_id="ent_enemy_test_01",
        name="Test Enemy",
        description="Unit test enemy",
        race_id="race_human_01",
        archetype_id="arc_warrior_01",
        weapon_ids=["wpn_longsword_01"],
        enemy_instance_id="enemy_inst_01",
        data_dir=DATA_DIR,
    )

    assert enemy.enemy_instance_id == "enemy_inst_01"
    assert enemy.hp == 16
    assert enemy.AC == 13
    assert enemy.initiative_mod == 1
    assert [weapon.id for weapon in enemy.weapons] == ["wpn_longsword_01"]


def test_load_enemy_registry_includes_persona():
    from core.registry.enemy_registry import load_enemy_model_registry

    enemies = load_enemy_model_registry(DATA_DIR)

    assert "ent_fireborn_sage_01" in enemies
    enemy = enemies["ent_fireborn_sage_01"]
    assert enemy.persona == "calculated, patient — casts control spells first, then exploits vulnerabilities"


def test_load_player_templates_returns_entity_records_without_instance_ids():
    players = load_player_registry(DATA_DIR)

    assert "ent_human_warrior_01" in players
    player_template = players["ent_human_warrior_01"]
    assert player_template.id == "ent_human_warrior_01"
    assert player_template.race.id == "race_human_01"
    assert player_template.archetype.id == "arc_warrior_01"
    assert player_template.initiative_mod == 1
    assert [weapon.id for weapon in player_template.weapons] == ["wpn_longsword_01"]
    assert not hasattr(player_template, "player_instance_id")


def test_load_enemy_templates_returns_entity_records_without_instance_ids():
    enemies = load_enemy_registry(DATA_DIR)

    assert "ent_fireborn_sage_01" in enemies
    enemy_template = enemies["ent_fireborn_sage_01"]
    assert enemy_template.id == "ent_fireborn_sage_01"
    assert enemy_template.race.id == "race_fireborn_01"
    assert enemy_template.archetype.id == "arc_sage_01"
    assert enemy_template.initiative_mod == 2
    assert [weapon.id for weapon in enemy_template.weapons] == ["wpn_staff_01"]
    assert not hasattr(enemy_template, "enemy_instance_id")


def test_load_enemy_templates_raises_on_enemy_schema_violation(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
        "players.json",
        "enemies.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    enemies = json.loads((data_copy / "enemies.json").read_text(encoding="utf-8"))
    enemies[0].pop("name")
    (data_copy / "enemies.json").write_text(json.dumps(enemies, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="Schema validation failed for 'enemies.json'"):
        load_enemy_registry(data_copy)


def test_load_player_templates_raises_on_unknown_reference(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
        "players.json",
        "enemies.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    players = json.loads((data_copy / "players.json").read_text(encoding="utf-8"))
    players[0]["race"] = "race_missing_999"
    (data_copy / "players.json").write_text(json.dumps(players, indent=2), encoding="utf-8")

    with pytest.raises(KeyError, match="Unknown race id 'race_missing_999'"):
        load_player_registry(data_copy)


def test_load_dungeon_templates_resolves_enemy_references():
    dungeons = load_dungeon_registry(DATA_DIR)

    assert "dgn_ember_catacombs_01" in dungeons
    dungeon = dungeons["dgn_ember_catacombs_01"]
    assert dungeon.start_room == "room_entrance_01"
    assert len(dungeon.rooms) == 3

    first_encounter = dungeon.rooms[0].encounters[0]
    assert [enemy.id for enemy in first_encounter.enemies] == ["ent_fireborn_sage_01"]


def test_load_dungeon_templates_raises_on_unknown_enemy_reference(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
        "players.json",
        "enemies.json",
        "dungeons.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    dungeons = json.loads((data_copy / "dungeons.json").read_text(encoding="utf-8"))
    dungeons[0]["rooms"][0]["encounters"][0]["enemies"] = ["ent_missing_999"]
    (data_copy / "dungeons.json").write_text(json.dumps(dungeons, indent=2), encoding="utf-8")

    with pytest.raises(KeyError, match="Unknown enemy id 'ent_missing_999'"):
        load_dungeon_registry(data_copy)


def test_load_dungeon_templates_raises_on_unknown_room_connection(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
        "players.json",
        "enemies.json",
        "dungeons.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    dungeons = json.loads((data_copy / "dungeons.json").read_text(encoding="utf-8"))
    dungeons[0]["rooms"][0]["connections"].append("room_missing_999")
    (data_copy / "dungeons.json").write_text(json.dumps(dungeons, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="references unknown connection 'room_missing_999'"):
        load_dungeon_registry(data_copy)


def test_load_dungeon_templates_raises_on_unreachable_end_room(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
        "players.json",
        "enemies.json",
        "dungeons.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    dungeons = json.loads((data_copy / "dungeons.json").read_text(encoding="utf-8"))
    dungeons[0]["rooms"][1]["connections"] = ["room_entrance_01"]
    (data_copy / "dungeons.json").write_text(json.dumps(dungeons, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="is not reachable from start_room"):
        load_dungeon_registry(data_copy)


def test_load_dungeon_templates_raises_on_unknown_start_room(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
        "players.json",
        "enemies.json",
        "dungeons.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    dungeons = json.loads((data_copy / "dungeons.json").read_text(encoding="utf-8"))
    dungeons[0]["start_room"] = "room_missing_999"
    (data_copy / "dungeons.json").write_text(json.dumps(dungeons, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown start_room 'room_missing_999'"):
        load_dungeon_registry(data_copy)


def test_load_catalog_raises_on_schema_violation(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
        "players.json",
        "enemies.json",
        "dungeons.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    # Schema should reject additional properties.
    attacks = json.loads((data_copy / "attacks.json").read_text(encoding="utf-8"))
    attacks[0]["unexpected_field"] = "boom"
    (data_copy / "attacks.json").write_text(json.dumps(attacks, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="Schema validation failed for 'attacks.json'"):
        load_catalog_registry(data_copy)


def test_load_player_templates_raises_on_player_schema_violation(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
        "players.json",
        "enemies.json",
        "dungeons.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    players = json.loads((data_copy / "players.json").read_text(encoding="utf-8"))
    players[0].pop("name")
    (data_copy / "players.json").write_text(json.dumps(players, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="Schema validation failed for 'players.json'"):
        load_player_registry(data_copy)


def test_load_dungeon_templates_raises_on_schema_violation(tmp_path: Path):
    data_copy = tmp_path / "data"
    data_copy.mkdir(parents=True, exist_ok=True)

    for file_name in [
        "status_effects.json",
        "attacks.json",
        "spells.json",
        "weapons.json",
        "races.json",
        "archetypes.json",
        "players.json",
        "enemies.json",
        "dungeons.json",
    ]:
        source = DATA_DIR / file_name
        target = data_copy / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    dungeons = json.loads((data_copy / "dungeons.json").read_text(encoding="utf-8"))
    dungeons[0].pop("start_room")
    (data_copy / "dungeons.json").write_text(json.dumps(dungeons, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="Schema validation failed for 'dungeons.json'"):
        load_dungeon_registry(data_copy)

import json
from pathlib import Path

import pytest

from util.dataloader import create_entity_from_ids, load_catalog


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def test_load_catalog_resolves_id_references():
    catalog = load_catalog(DATA_DIR)

    fire_arrow = catalog.attacks["atk_fire_arrow_01"]
    assert fire_arrow.status_effects is not None
    assert [effect.id for effect in fire_arrow.status_effects] == ["se_dot_fire_01"]

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
    attacks[1]["status_effects"] = ["se_missing_999"]
    (data_copy / "attacks.json").write_text(json.dumps(attacks, indent=2), encoding="utf-8")

    with pytest.raises(KeyError, match="se_missing_999"):
        load_catalog(data_copy)

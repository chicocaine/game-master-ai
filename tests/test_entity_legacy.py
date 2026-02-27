from models.entity import Entity


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
        "id": "ent_legacy_01",
        "name": "Legacy Entity",
        "description": "compat test",
        "race": {
            "id": "race_test_01",
            "name": "Test Race",
            "description": "race",
            "base_hp": 10,
            "base_AC": 11,
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
        "known_attacks": [],
        "known_spells": [],
        "resistances": [],
        "immunities": [],
        "vulnerabilities": [],
    }


def test_from_dict_accepts_legacy_single_weapon_field():
    payload = _base_entity_payload()
    payload["weapon"] = _weapon_dict("wpn_legacy_01")

    entity = Entity.from_dict(payload)

    assert [weapon.id for weapon in entity.weapons] == ["wpn_legacy_01"]
    assert entity.weapon.id == "wpn_legacy_01"
    assert entity.hp == 12
    assert entity.max_hp == 12
    assert entity.base_AC == 12
    assert entity.AC == 12
    assert entity.spell_slots == 0
    assert entity.max_spell_slots == 0


def test_from_dict_prefers_weapons_list_when_present():
    payload = _base_entity_payload()
    payload["weapon"] = _weapon_dict("wpn_legacy_ignored")
    payload["weapons"] = [
        _weapon_dict("wpn_new_01", proficiency="martial", handling="versatile"),
        _weapon_dict("wpn_new_02", proficiency="arcane", delivery="ranged", magic_type="focus"),
    ]

    entity = Entity.from_dict(payload)

    assert [weapon.id for weapon in entity.weapons] == ["wpn_new_01", "wpn_new_02"]
    assert entity.weapon.id == "wpn_new_01"


def test_from_dict_uses_empty_weapons_when_none_provided():
    payload = _base_entity_payload()

    entity = Entity.from_dict(payload)

    assert entity.weapons == []
    assert entity.weapon.id == ""

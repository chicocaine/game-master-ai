"""Tests for intent-to-action mapping."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.action_mapper import ActionMapper
from agent.parser import ParsedIntent
from models.actions import ActionType, RestType
from models.data_loader import DataLoader
from models.entities import Entity, EntityType, SpellSlots
from models.states import EncounterState, GlobalGameState, GameMode


def _make_player(entity_id: str, name: str) -> Entity:
    return Entity(
        entity_id=entity_id,
        name=name,
        entity_type=EntityType.PLAYER,
        race="Human",
        char_class="Wizard",
        hp=10,
        max_hp=10,
        ac=12,
        attack_modifier=2,
        known_attacks=["staff_strike"],
        known_spells=["fire_bolt", "poison_cloud", "heal"],
        spell_slots=SpellSlots(current=2, max=2),
    )


def _make_enemy(entity_id: str, name: str) -> Entity:
    return Entity(
        entity_id=entity_id,
        name=name,
        entity_type=EntityType.ENEMY,
        race="Goblin",
        char_class="Fighter",
        hp=8,
        max_hp=8,
        ac=11,
        attack_modifier=1,
        known_attacks=["goblin_slash"],
        known_spells=[],
        spell_slots=SpellSlots(current=0, max=0),
    )


def _intent(intent: str, **kwargs) -> ParsedIntent:
    return ParsedIntent(intent=intent, confidence=1.0, raw_text="test", **kwargs)


def test_attack_infers_attack_and_target():
    loader = DataLoader("data")
    loader.load_all()
    mapper = ActionMapper(loader)

    player = _make_player("player_1", "Arin")
    enemy = _make_enemy("enemy_1", "Goblin")
    encounter = EncounterState(
        encounter_id="encounter_1",
        room_id="room_1",
        entities=[player, enemy],
        initiative_order=["player_1", "enemy_1"],
        active_entity_id="player_1",
    )

    result = mapper.map_intent(
        parsed=_intent(ActionType.ATTACK.value),
        actor=player,
        encounter_state=encounter,
    )

    assert result.action is not None
    assert result.action.action_type == ActionType.ATTACK
    assert result.action.target_id == "enemy_1"
    assert result.action.parameters.get("attack_id") == "staff_strike"


def test_attack_requires_target_when_multiple_enemies():
    loader = DataLoader("data")
    loader.load_all()
    mapper = ActionMapper(loader)

    player = _make_player("player_1", "Arin")
    enemy_a = _make_enemy("enemy_1", "Goblin A")
    enemy_b = _make_enemy("enemy_2", "Goblin B")
    encounter = EncounterState(
        encounter_id="encounter_1",
        room_id="room_1",
        entities=[player, enemy_a, enemy_b],
        initiative_order=["player_1", "enemy_1", "enemy_2"],
        active_entity_id="player_1",
    )

    result = mapper.map_intent(
        parsed=_intent(ActionType.ATTACK.value),
        actor=player,
        encounter_state=encounter,
    )

    assert result.action is None
    assert result.needs_clarification


def test_cast_spell_aoe_clears_target():
    loader = DataLoader("data")
    loader.load_all()
    mapper = ActionMapper(loader)

    player = _make_player("player_1", "Arin")
    enemy = _make_enemy("enemy_1", "Goblin")
    encounter = EncounterState(
        encounter_id="encounter_1",
        room_id="room_1",
        entities=[player, enemy],
        initiative_order=["player_1", "enemy_1"],
        active_entity_id="player_1",
    )

    result = mapper.map_intent(
        parsed=_intent(ActionType.CAST_SPELL.value, spell_id="poison_cloud", target_id="enemy_1"),
        actor=player,
        encounter_state=encounter,
    )

    assert result.action is not None
    assert result.action.action_type == ActionType.CAST_SPELL
    assert result.action.parameters.get("spell_id") == "poison_cloud"
    assert result.action.target_id is None


def test_cast_spell_infers_single_enemy_target():
    loader = DataLoader("data")
    loader.load_all()
    mapper = ActionMapper(loader)

    player = _make_player("player_1", "Arin")
    enemy = _make_enemy("enemy_1", "Goblin")
    encounter = EncounterState(
        encounter_id="encounter_1",
        room_id="room_1",
        entities=[player, enemy],
        initiative_order=["player_1", "enemy_1"],
        active_entity_id="player_1",
    )

    result = mapper.map_intent(
        parsed=_intent(ActionType.CAST_SPELL.value, spell_id="fire_bolt"),
        actor=player,
        encounter_state=encounter,
    )

    assert result.action is not None
    assert result.action.target_id == "enemy_1"


def test_cast_spell_requires_target_when_multiple_enemies():
    loader = DataLoader("data")
    loader.load_all()
    mapper = ActionMapper(loader)

    player = _make_player("player_1", "Arin")
    enemy_a = _make_enemy("enemy_1", "Goblin A")
    enemy_b = _make_enemy("enemy_2", "Goblin B")
    encounter = EncounterState(
        encounter_id="encounter_1",
        room_id="room_1",
        entities=[player, enemy_a, enemy_b],
        initiative_order=["player_1", "enemy_1", "enemy_2"],
        active_entity_id="player_1",
    )

    result = mapper.map_intent(
        parsed=_intent(ActionType.CAST_SPELL.value, spell_id="fire_bolt"),
        actor=player,
        encounter_state=encounter,
    )

    assert result.action is None
    assert result.needs_clarification


def test_cast_spell_ally_requires_target_with_multiple_allies():
    loader = DataLoader("data")
    loader.load_all()
    mapper = ActionMapper(loader)

    player = _make_player("player_1", "Arin")
    ally = _make_player("player_2", "Mara")
    encounter = EncounterState(
        encounter_id="encounter_1",
        room_id="room_1",
        entities=[player, ally],
        initiative_order=["player_1", "player_2"],
        active_entity_id="player_1",
    )

    result = mapper.map_intent(
        parsed=_intent(ActionType.CAST_SPELL.value, spell_id="heal"),
        actor=player,
        encounter_state=encounter,
    )

    assert result.action is None
    assert result.needs_clarification


def test_cast_spell_self_target_rule_sets_actor():
    loader = DataLoader("data")
    loader.load_all()
    loader.spells["self_shield"] = {
        "id": "self_shield",
        "name": "Self Shield",
        "category": "status",
        "target": "self",
        "cost": 1,
        "status_effect": {
            "type": "fortified",
            "duration": 2,
            "magnitude": 1,
        },
    }

    mapper = ActionMapper(loader)
    player = _make_player("player_1", "Arin")
    encounter = EncounterState(
        encounter_id="encounter_1",
        room_id="room_1",
        entities=[player],
        initiative_order=["player_1"],
        active_entity_id="player_1",
    )

    result = mapper.map_intent(
        parsed=_intent(ActionType.CAST_SPELL.value, spell_id="self_shield"),
        actor=player,
        encounter_state=encounter,
    )

    assert result.action is not None
    assert result.action.target_id == "player_1"


def test_cast_spell_ally_target_explicit():
    loader = DataLoader("data")
    loader.load_all()
    mapper = ActionMapper(loader)

    player = _make_player("player_1", "Arin")
    ally = _make_player("player_2", "Mara")
    encounter = EncounterState(
        encounter_id="encounter_1",
        room_id="room_1",
        entities=[player, ally],
        initiative_order=["player_1", "player_2"],
        active_entity_id="player_1",
    )

    result = mapper.map_intent(
        parsed=_intent(ActionType.CAST_SPELL.value, spell_id="heal", target_id="player_2"),
        actor=player,
        encounter_state=encounter,
    )

    assert result.action is not None
    assert result.action.target_id == "player_2"


def test_move_infers_single_connection():
    loader = DataLoader("data")
    loader.load_all()
    mapper = ActionMapper(loader)

    player = _make_player("player_1", "Arin")
    global_state = GlobalGameState(
        game_mode=GameMode.EXPLORATION,
        current_dungeon_id="crypt_of_whispers",
        current_room_id="room_entrance",
        players=[player],
    )

    result = mapper.map_intent(
        parsed=_intent(ActionType.MOVE.value),
        actor=player,
        global_state=global_state,
    )

    assert result.action is not None
    assert result.action.action_type == ActionType.MOVE
    assert result.action.target_id == "room_hallway"


def test_rest_defaults_to_short():
    mapper = ActionMapper()
    player = _make_player("player_1", "Arin")

    result = mapper.map_intent(
        parsed=_intent(ActionType.REST.value),
        actor=player,
    )

    assert result.action is not None
    assert result.action.action_type == ActionType.REST
    assert result.action.parameters.get("rest_type") == RestType.SHORT.value


def test_unknown_intent_requests_clarification():
    mapper = ActionMapper()
    player = _make_player("player_1", "Arin")

    result = mapper.map_intent(
        parsed=_intent("unknown"),
        actor=player,
    )

    assert result.action is None
    assert result.needs_clarification


def main() -> bool:
    tests = [
        test_attack_infers_attack_and_target,
        test_attack_requires_target_when_multiple_enemies,
        test_cast_spell_aoe_clears_target,
        test_cast_spell_infers_single_enemy_target,
        test_cast_spell_requires_target_when_multiple_enemies,
        test_cast_spell_ally_requires_target_with_multiple_allies,
        test_cast_spell_self_target_rule_sets_actor,
        test_cast_spell_ally_target_explicit,
        test_move_infers_single_connection,
        test_rest_defaults_to_short,
        test_unknown_intent_requests_clarification,
    ]

    for test in tests:
        test()
    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("All action mapper tests passed.")
    except AssertionError as exc:
        print(f"Test failed: {exc}")
        raise

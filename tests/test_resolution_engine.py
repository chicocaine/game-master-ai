"""Tests for the resolution engine."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import resolution as resolution_module
from engine.resolution import ResolutionEngine
from models.actions import RestAction, CastSpellAction, AttackAction, RestType
from models.entities import Entity, EntityType, SpellSlots, StatusEffect
from models.states import GlobalGameState, EncounterState, GameMode
from models.data_loader import DataLoader
from utils.dice import RollResult


def _make_player(entity_id: str, name: str, hp: int, max_hp: int) -> Entity:
    return Entity(
        entity_id=entity_id,
        name=name,
        entity_type=EntityType.PLAYER,
        race="Human",
        char_class="Fighter",
        hp=hp,
        max_hp=max_hp,
        ac=12,
        attack_modifier=2,
        known_attacks=["staff_strike"],
        known_spells=["fire_bolt", "heal", "sleep", "poison_cloud"],
        spell_slots=SpellSlots(current=2, max=2),
    )


def _make_enemy(entity_id: str, name: str, hp: int, max_hp: int) -> Entity:
    return Entity(
        entity_id=entity_id,
        name=name,
        entity_type=EntityType.ENEMY,
        race="Goblin",
        char_class="Fighter",
        hp=hp,
        max_hp=max_hp,
        ac=11,
        attack_modifier=1,
        known_attacks=["goblin_slash"],
        known_spells=[],
        spell_slots=SpellSlots(current=0, max=0),
    )


def _with_stubbed_dice(d20_value: int, dice_total: int):
    original_roll_d20 = resolution_module.roll_d20
    original_roll_dice = resolution_module.roll_dice

    def stub_d20():
        return d20_value

    def stub_dice(expression: str):
        return RollResult(
            total=dice_total,
            rolls=[dice_total],
            modifier=0,
            expression=expression,
        )

    resolution_module.roll_d20 = stub_d20
    resolution_module.roll_dice = stub_dice

    def restore():
        resolution_module.roll_d20 = original_roll_d20
        resolution_module.roll_dice = original_roll_dice

    return restore


def test_attack_hit():
    loader = DataLoader("data")
    loader.load_all()
    engine = ResolutionEngine(loader)

    player = _make_player("player_1", "Arin", 18, 18)
    enemy = _make_enemy("enemy_1", "Goblin", 8, 8)
    encounter = EncounterState(
        encounter_id="goblin_patrol",
        room_id="room_1",
        entities=[player, enemy],
        initiative_order=["player_1", "enemy_1"],
        active_entity_id="player_1",
    )

    restore = _with_stubbed_dice(d20_value=20, dice_total=4)
    try:
        action = AttackAction("player_1", "enemy_1", "staff_strike")
        result = engine.resolve_action(
            action,
            GlobalGameState(game_mode=GameMode.ENCOUNTER),
            encounter,
        )
        assert result.success
        assert result.details["hit"] is True
        assert enemy.hp == 4
    finally:
        restore()


def test_attack_miss():
    loader = DataLoader("data")
    loader.load_all()
    engine = ResolutionEngine(loader)

    player = _make_player("player_1", "Arin", 18, 18)
    enemy = _make_enemy("enemy_1", "Goblin", 8, 8)
    enemy.ac = 20
    encounter = EncounterState(
        encounter_id="goblin_patrol",
        room_id="room_1",
        entities=[player, enemy],
        initiative_order=["player_1", "enemy_1"],
        active_entity_id="player_1",
    )

    restore = _with_stubbed_dice(d20_value=1, dice_total=4)
    try:
        action = AttackAction("player_1", "enemy_1", "staff_strike")
        result = engine.resolve_action(
            action,
            GlobalGameState(game_mode=GameMode.ENCOUNTER),
            encounter,
        )
        assert result.success
        assert result.details["hit"] is False
        assert enemy.hp == 8
    finally:
        restore()


def test_spell_damage_consumes_slot():
    loader = DataLoader("data")
    loader.load_all()
    engine = ResolutionEngine(loader)

    player = _make_player("player_1", "Arin", 18, 18)
    enemy = _make_enemy("enemy_1", "Goblin", 8, 8)
    encounter = EncounterState(
        encounter_id="goblin_patrol",
        room_id="room_1",
        entities=[player, enemy],
        initiative_order=["player_1", "enemy_1"],
        active_entity_id="player_1",
    )

    restore = _with_stubbed_dice(d20_value=10, dice_total=5)
    try:
        action = CastSpellAction("player_1", "fire_bolt", "enemy_1")
        result = engine.resolve_action(
            action,
            GlobalGameState(game_mode=GameMode.ENCOUNTER),
            encounter,
        )
        assert result.success
        assert enemy.hp == 3
        assert player.spell_slots.current == 1
    finally:
        restore()


def test_spell_heal_clamps_to_max():
    loader = DataLoader("data")
    loader.load_all()
    engine = ResolutionEngine(loader)

    player = _make_player("player_1", "Arin", 5, 10)
    ally = _make_player("player_2", "Mara", 3, 10)
    encounter = EncounterState(
        encounter_id="heal_test",
        room_id="room_1",
        entities=[player, ally],
        initiative_order=["player_1", "player_2"],
        active_entity_id="player_1",
    )

    restore = _with_stubbed_dice(d20_value=10, dice_total=10)
    try:
        action = CastSpellAction("player_1", "heal", "player_2")
        result = engine.resolve_action(
            action,
            GlobalGameState(game_mode=GameMode.ENCOUNTER),
            encounter,
        )
        assert result.success
        assert ally.hp == 10
        assert player.spell_slots.current == 1
    finally:
        restore()


def test_spell_status_applies_and_refreshes():
    loader = DataLoader("data")
    loader.load_all()
    engine = ResolutionEngine(loader)

    player = _make_player("player_1", "Arin", 18, 18)
    enemy = _make_enemy("enemy_1", "Goblin", 8, 8)
    player.spell_slots.current = 2
    encounter = EncounterState(
        encounter_id="status_test",
        room_id="room_1",
        entities=[player, enemy],
        initiative_order=["player_1", "enemy_1"],
        active_entity_id="player_1",
    )

    action = CastSpellAction("player_1", "sleep", "enemy_1")
    result = engine.resolve_action(
        action,
        GlobalGameState(game_mode=GameMode.ENCOUNTER),
        encounter,
    )
    assert result.success
    assert enemy.has_status_effect("stunned")

    action_again = CastSpellAction("player_1", "sleep", "enemy_1")
    result_again = engine.resolve_action(
        action_again,
        GlobalGameState(game_mode=GameMode.ENCOUNTER),
        encounter,
    )
    assert result_again.success
    effects = [e for e in enemy.status_effects if e.effect_type == "stunned"]
    assert len(effects) == 1


def test_spell_no_slots_fails():
    loader = DataLoader("data")
    loader.load_all()
    engine = ResolutionEngine(loader)

    player = _make_player("player_1", "Arin", 18, 18)
    enemy = _make_enemy("enemy_1", "Goblin", 8, 8)
    player.spell_slots.current = 0
    encounter = EncounterState(
        encounter_id="goblin_patrol",
        room_id="room_1",
        entities=[player, enemy],
        initiative_order=["player_1", "enemy_1"],
        active_entity_id="player_1",
    )

    action = CastSpellAction("player_1", "fire_bolt", "enemy_1")
    result = engine.resolve_action(
        action,
        GlobalGameState(game_mode=GameMode.ENCOUNTER),
        encounter,
    )
    assert result.success is False
    assert enemy.hp == 8


def test_status_effect_start_of_turn():
    loader = DataLoader("data")
    loader.load_all()
    engine = ResolutionEngine(loader)

    enemy = _make_enemy("enemy_1", "Goblin", 6, 6)
    enemy.add_status_effect(StatusEffect(effect_type="poisoned", duration=2, magnitude=2))

    encounter = EncounterState(
        encounter_id="status_test",
        room_id="room_1",
        entities=[enemy],
        initiative_order=["enemy_1"],
        active_entity_id="enemy_1",
    )

    result = engine.resolve_start_of_turn(enemy, encounter)
    assert result["triggered"][0]["damage_applied"] == 2
    assert enemy.hp == 4
    remaining = enemy.get_status_effect("poisoned")
    assert remaining is not None
    assert remaining.duration == 1

    result = engine.resolve_start_of_turn(enemy, encounter)
    assert result["triggered"][0]["damage_applied"] == 2
    assert enemy.hp == 2
    assert enemy.get_status_effect("poisoned") is None


def test_rest_short_and_long():
    loader = DataLoader("data")
    loader.load_all()
    engine = ResolutionEngine(loader)

    player = _make_player("player_1", "Arin", 4, 10)
    player.spell_slots.current = 0
    global_state = GlobalGameState(
        game_mode=GameMode.EXPLORATION,
        current_room_id="room_1",
        players=[player],
    )

    action = RestAction("player_1", RestType.SHORT)
    result = engine.resolve_action(action, global_state)
    assert result.success
    assert player.hp == 6
    assert player.spell_slots.current == 1
    assert global_state.dungeon_state.has_rested_in("room_1")

    global_state.dungeon_state.rested_rooms = []
    action = RestAction("player_1", RestType.LONG)
    result = engine.resolve_action(action, global_state)
    assert result.success
    assert player.hp == 10
    assert player.spell_slots.current == 2


if __name__ == "__main__":
    try:
        test_attack_hit()
        test_attack_miss()
        test_spell_damage_consumes_slot()
        test_spell_heal_clamps_to_max()
        test_spell_status_applies_and_refreshes()
        test_spell_no_slots_fails()
        test_status_effect_start_of_turn()
        test_rest_short_and_long()
        print("\n✅ All resolution engine tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

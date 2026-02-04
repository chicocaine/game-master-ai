"""Quick test to verify data layer implementation."""

from models import (
    Entity,
    EntityType,
    SpellSlots,
    StatusEffect,
    GlobalGameState,
    EncounterState,
    GameMode,
    Action,
    ActionType,
)


def test_entity():
    """Test entity creation and methods."""
    print("Testing Entity...")
    
    player = Entity(
        entity_id="player_1",
        name="Arin",
        entity_type=EntityType.PLAYER,
        race="Elf",
        char_class="Wizard",
        hp=18,
        max_hp=18,
        ac=12,
        attack_modifier=2,
        known_spells=["fire_bolt"],
        spell_slots=SpellSlots(current=3, max=3),
    )
    
    assert player.is_alive()
    assert player.hp == 18
    
    # Test damage
    damage_taken = player.take_damage(5)
    assert damage_taken == 5
    assert player.hp == 13
    
    # Test healing
    healed = player.heal(10)
    assert healed == 5
    assert player.hp == 18
    
    # Test status effects
    effect = StatusEffect(effect_type="poisoned", duration=2, magnitude=1)
    player.add_status_effect(effect)
    assert player.has_status_effect("poisoned")
    
    # Test spell slots
    assert player.spell_slots.use_slot()
    assert player.spell_slots.current == 2
    
    # Test serialization
    data = player.to_dict()
    restored = Entity.from_dict(data)
    assert restored.name == "Arin"
    assert restored.hp == 18
    
    print("✓ Entity tests passed")


def test_game_state():
    """Test game state."""
    print("Testing GlobalGameState...")
    
    player = Entity(
        entity_id="player_1",
        name="Arin",
        entity_type=EntityType.PLAYER,
        race="Elf",
        char_class="Wizard",
        hp=18,
        max_hp=18,
        ac=12,
        attack_modifier=2,
        spell_slots=SpellSlots(current=3, max=3),
    )
    
    state = GlobalGameState(
        game_mode=GameMode.EXPLORATION,
        current_dungeon_id="crypt_01",
        current_room_id="room_entrance",
        players=[player],
    )
    
    assert state.game_mode == GameMode.EXPLORATION
    assert len(state.get_living_players()) == 1
    assert not state.all_players_dead()
    
    # Test progression
    state.mark_encounter_cleared("encounter_001", 50)
    assert state.has_cleared_encounter("encounter_001")
    assert state.progression.total_rewards == 50
    assert state.progression.encounters_cleared == 1
    
    # Test serialization
    data = state.to_dict()
    restored = GlobalGameState.from_dict(data)
    assert restored.current_dungeon_id == "crypt_01"
    assert restored.progression.total_rewards == 50
    
    print("✓ GlobalGameState tests passed")


def test_encounter_state():
    """Test encounter state."""
    print("Testing EncounterState...")
    
    player = Entity(
        entity_id="player_1",
        name="Arin",
        entity_type=EntityType.PLAYER,
        race="Elf",
        char_class="Wizard",
        hp=18,
        max_hp=18,
        ac=12,
        attack_modifier=2,
        spell_slots=SpellSlots(current=3, max=3),
    )
    
    enemy = Entity(
        entity_id="enemy_1",
        name="Goblin",
        entity_type=EntityType.ENEMY,
        race="Goblin",
        char_class="Fighter",
        hp=8,
        max_hp=8,
        ac=11,
        attack_modifier=1,
    )
    
    encounter = EncounterState(
        encounter_id="goblin_patrol",
        room_id="room_2",
        round=1,
        entities=[player, enemy],
        initiative_order=["player_1", "enemy_1"],
        active_entity_id="player_1",
    )
    
    assert encounter.round == 1
    assert encounter.get_active_entity().name == "Arin"
    assert len(encounter.get_living_players()) == 1
    assert len(encounter.get_living_enemies()) == 1
    assert not encounter.all_enemies_dead()
    
    # Test turn advancement
    encounter.advance_turn()
    assert encounter.active_entity_id == "enemy_1"
    
    encounter.advance_turn()
    assert encounter.active_entity_id == "player_1"
    assert encounter.round == 2
    
    # Test combat log
    encounter.append_log("Combat begins!")
    assert len(encounter.combat_log) == 1
    
    print("✓ EncounterState tests passed")


def test_action():
    """Test action models."""
    print("Testing Actions...")
    
    action = Action(
        actor_id="player_1",
        action_type=ActionType.ATTACK,
        target_id="enemy_1",
        parameters={"attack_id": "staff_strike"},
    )
    
    assert action.actor_id == "player_1"
    assert action.action_type == ActionType.ATTACK
    
    # Test serialization
    data = action.to_dict()
    restored = Action.from_dict(data)
    assert restored.target_id == "enemy_1"
    assert restored.parameters["attack_id"] == "staff_strike"
    
    print("✓ Action tests passed")


if __name__ == "__main__":
    try:
        test_entity()
        test_game_state()
        test_encounter_state()
        test_action()
        print("\n✅ All data layer tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

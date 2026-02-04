"""Test the data loader with sample data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import DataLoader


def main():
    """Test loading and validating sample data."""
    print("Loading game data...")
    loader = DataLoader("data")
    
    if not loader.load_all():
        print("❌ Failed to load data")
        return False
    
    print("\nValidating data...")
    errors = loader.validate_data()
    
    if errors:
        print(f"❌ Found {len(errors)} validation errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ All data loaded and validated successfully!")
    
    # Print summary
    print(f"\nData Summary:")
    print(f"  Dungeons: {len(loader.dungeons)}")
    print(f"  Encounters: {len(loader.encounters)}")
    print(f"  Spells: {len(loader.spells)}")
    print(f"  Attacks: {len(loader.attacks)}")
    print(f"  Enemies: {len(loader.enemies)}")
    print(f"  Classes: {len(loader.classes)}")
    print(f"  Races: {len(loader.races)}")
    
    # Show sample dungeon
    dungeon = loader.get_dungeon("crypt_of_whispers")
    if dungeon:
        print(f"\n📍 Sample Dungeon: {dungeon['name']}")
        print(f"   Description: {dungeon['description']}")
        print(f"   Rooms: {len(dungeon['rooms'])}")
        print(f"   Start Room: {dungeon['start_room']}")
        print(f"   Exit Room: {dungeon['exit_room']}")
    
    # Show sample encounter
    encounter = loader.get_encounter("goblin_patrol")
    if encounter:
        print(f"\n⚔️  Sample Encounter: {encounter['name']}")
        print(f"   Enemies: {encounter['enemies']}")
        print(f"   Reward: {encounter['reward']}")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

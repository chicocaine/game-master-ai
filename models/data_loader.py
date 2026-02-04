"""Data loaders for game data files (dungeons, encounters, spells, attacks)."""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path


class DataLoader:
    """Loads and validates game data from JSON files."""

    def __init__(self, data_dir: str = "data"):
        """Initialize data loader with path to data directory."""
        self.data_dir = Path(data_dir)
        self.dungeons: Dict[str, dict] = {}
        self.encounters: Dict[str, dict] = {}
        self.spells: Dict[str, dict] = {}
        self.attacks: Dict[str, dict] = {}
        self.enemies: Dict[str, dict] = {}
        self.classes: Dict[str, dict] = {}
        self.races: Dict[str, dict] = {}

    def load_all(self) -> bool:
        """Load all game data files. Returns True if successful."""
        try:
            self.load_dungeons()
            self.load_encounters()
            self.load_spells()
            self.load_attacks()
            self.load_enemies()
            self.load_classes()
            self.load_races()
            return True
        except Exception as e:
            print(f"Error loading game data: {e}")
            return False

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Load a single JSON file from data directory."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            return json.load(f)

    def load_dungeons(self) -> None:
        """Load dungeon definitions."""
        try:
            data = self.load_json("dungeons.json")
            self.dungeons = {d["dungeon_id"]: d for d in data.get("dungeons", [])}
            print(f"Loaded {len(self.dungeons)} dungeons")
        except FileNotFoundError:
            print("Warning: dungeons.json not found")
            self.dungeons = {}

    def load_encounters(self) -> None:
        """Load encounter definitions."""
        try:
            data = self.load_json("encounters.json")
            self.encounters = {e["id"]: e for e in data.get("encounters", [])}
            print(f"Loaded {len(self.encounters)} encounters")
        except FileNotFoundError:
            print("Warning: encounters.json not found")
            self.encounters = {}

    def load_spells(self) -> None:
        """Load spell definitions."""
        try:
            data = self.load_json("spells.json")
            self.spells = {s["id"]: s for s in data.get("spells", [])}
            print(f"Loaded {len(self.spells)} spells")
        except FileNotFoundError:
            print("Warning: spells.json not found")
            self.spells = {}

    def load_attacks(self) -> None:
        """Load attack definitions."""
        try:
            data = self.load_json("attacks.json")
            self.attacks = {a["id"]: a for a in data.get("attacks", [])}
            print(f"Loaded {len(self.attacks)} attacks")
        except FileNotFoundError:
            print("Warning: attacks.json not found")
            self.attacks = {}

    def load_enemies(self) -> None:
        """Load enemy definitions."""
        try:
            data = self.load_json("enemies.json")
            self.enemies = {e["id"]: e for e in data.get("enemies", [])}
            print(f"Loaded {len(self.enemies)} enemy templates")
        except FileNotFoundError:
            print("Warning: enemies.json not found")
            self.enemies = {}

    def load_classes(self) -> None:
        """Load character class definitions."""
        try:
            data = self.load_json("classes.json")
            self.classes = {c["id"]: c for c in data.get("classes", [])}
            print(f"Loaded {len(self.classes)} character classes")
        except FileNotFoundError:
            print("Warning: classes.json not found")
            self.classes = {}

    def load_races(self) -> None:
        """Load character race definitions."""
        try:
            data = self.load_json("races.json")
            self.races = {r["id"]: r for r in data.get("races", [])}
            print(f"Loaded {len(self.races)} character races")
        except FileNotFoundError:
            print("Warning: races.json not found")
            self.races = {}

    # Getter methods
    def get_dungeon(self, dungeon_id: str) -> Optional[dict]:
        """Get dungeon by ID."""
        return self.dungeons.get(dungeon_id)

    def get_encounter(self, encounter_id: str) -> Optional[dict]:
        """Get encounter by ID."""
        return self.encounters.get(encounter_id)

    def get_spell(self, spell_id: str) -> Optional[dict]:
        """Get spell by ID."""
        return self.spells.get(spell_id)

    def get_attack(self, attack_id: str) -> Optional[dict]:
        """Get attack by ID."""
        return self.attacks.get(attack_id)

    def get_enemy(self, enemy_id: str) -> Optional[dict]:
        """Get enemy template by ID."""
        return self.enemies.get(enemy_id)

    def get_class(self, class_id: str) -> Optional[dict]:
        """Get character class by ID."""
        return self.classes.get(class_id)

    def get_race(self, race_id: str) -> Optional[dict]:
        """Get character race by ID."""
        return self.races.get(race_id)

    def validate_data(self) -> List[str]:
        """Validate all loaded data. Returns list of errors."""
        errors = []

        # Validate dungeons
        for dungeon_id, dungeon in self.dungeons.items():
            # Check for required fields
            if "dungeon_id" not in dungeon:
                errors.append(f"Dungeon missing dungeon_id")
            if "start_room" not in dungeon:
                errors.append(f"Dungeon {dungeon_id} missing start_room")
            if "exit_room" not in dungeon:
                errors.append(f"Dungeon {dungeon_id} missing exit_room")
            if "rooms" not in dungeon:
                errors.append(f"Dungeon {dungeon_id} missing rooms")
                continue

            rooms = dungeon["rooms"]
            start_room = dungeon.get("start_room")
            exit_room = dungeon.get("exit_room")

            # Check if start_room exists
            if start_room and start_room not in rooms:
                errors.append(f"Dungeon {dungeon_id}: start_room '{start_room}' does not exist")

            # Check if exit_room exists
            if exit_room and exit_room not in rooms:
                errors.append(f"Dungeon {dungeon_id}: exit_room '{exit_room}' does not exist")

            # Validate rooms
            for room_id, room in rooms.items():
                if "connections" in room:
                    for conn in room["connections"]:
                        if conn not in rooms:
                            errors.append(
                                f"Dungeon {dungeon_id}, Room {room_id}: "
                                f"references unknown connected room '{conn}'"
                            )

                # Check encounter validity
                if room.get("encounter") and "encounter_id" in room:
                    enc_id = room["encounter_id"]
                    if enc_id not in self.encounters:
                        errors.append(
                            f"Dungeon {dungeon_id}, Room {room_id}: "
                            f"references unknown encounter '{enc_id}'"
                        )

        # Validate encounters
        for enc_id, encounter in self.encounters.items():
            if "enemies" not in encounter:
                errors.append(f"Encounter {enc_id} missing enemies list")
                continue

            for enemy_id in encounter["enemies"]:
                if enemy_id not in self.enemies:
                    errors.append(
                        f"Encounter {enc_id}: references unknown enemy template '{enemy_id}'"
                    )

        # Validate spells
        for spell_id, spell in self.spells.items():
            if "status_effect" in spell and spell["status_effect"]:
                effect_type = spell["status_effect"].get("type")
                # Could add more validation here for effect types

        # Validate attacks
        for attack_id, attack in self.attacks.items():
            if "damage" in attack:
                # Validate damage dice format (e.g., "1d6", "2d8+1")
                damage_str = attack["damage"]
                if not self._is_valid_dice_string(damage_str):
                    errors.append(f"Attack {attack_id}: invalid damage format '{damage_str}'")

        # Validate character classes
        for class_id, char_class in self.classes.items():
            for required_field in ["starting_hp", "base_ac", "attack_modifier"]:
                if required_field not in char_class:
                    errors.append(f"Class {class_id} missing required field: {required_field}")

        return errors

    @staticmethod
    def _is_valid_dice_string(dice_str: str) -> bool:
        """Check if a string is a valid dice notation (e.g., '1d6', '2d8+1')."""
        import re
        pattern = r'^(\d+)d(\d+)([+\-]\d+)?$'
        return bool(re.match(pattern, dice_str))

"""Entity models for players and enemies."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class EntityType(Enum):
    """Enumeration of entity types."""
    PLAYER = "player"
    ENEMY = "enemy"


@dataclass
class StatusEffect:
    """Represents a status effect applied to an entity."""
    effect_type: str  # "poisoned", "stunned", "burning", etc.
    duration: int  # Turns remaining
    magnitude: int = 1  # Intensity (damage per turn, modifier amount, etc.)
    source_id: Optional[str] = None  # Entity that applied the effect


@dataclass
class SpellSlots:
    """Represents spell slot management."""
    current: int
    max: int

    def use_slot(self) -> bool:
        """Attempt to use a spell slot. Returns True if successful."""
        if self.current > 0:
            self.current -= 1
            return True
        return False

    def restore(self, amount: int) -> None:
        """Restore spell slots (clamped to max)."""
        self.current = min(self.current + amount, self.max)

    def restore_all(self) -> None:
        """Fully restore spell slots."""
        self.current = self.max


@dataclass
class Entity:
    """Base entity class for players and enemies."""
    entity_id: str
    name: str
    entity_type: EntityType
    race: str
    char_class: str
    
    hp: int
    max_hp: int
    ac: int  # Armor Class
    attack_modifier: int
    
    known_attacks: List[str] = field(default_factory=list)
    spell_slots: SpellSlots = field(default_factory=lambda: SpellSlots(current=0, max=0))
    known_spells: List[str] = field(default_factory=list)
    status_effects: List[StatusEffect] = field(default_factory=list)

    def is_alive(self) -> bool:
        """Check if entity is alive."""
        return self.hp > 0

    def take_damage(self, amount: int) -> int:
        """Apply damage to entity. Returns actual damage taken."""
        actual_damage = min(amount, self.hp)
        self.hp = max(0, self.hp - amount)
        return actual_damage

    def heal(self, amount: int) -> int:
        """Heal entity. Returns actual healing applied."""
        actual_heal = min(amount, self.max_hp - self.hp)
        self.hp = min(self.hp + amount, self.max_hp)
        return actual_heal

    def add_status_effect(self, effect: StatusEffect) -> None:
        """Add a status effect to entity."""
        self.status_effects.append(effect)

    def remove_status_effect(self, effect_type: str) -> bool:
        """Remove all instances of a status effect type. Returns True if removed."""
        original_count = len(self.status_effects)
        self.status_effects = [e for e in self.status_effects if e.effect_type != effect_type]
        return len(self.status_effects) < original_count

    def has_status_effect(self, effect_type: str) -> bool:
        """Check if entity has a specific status effect."""
        return any(e.effect_type == effect_type for e in self.status_effects)

    def get_status_effect(self, effect_type: str) -> Optional[StatusEffect]:
        """Get the first status effect of a specific type."""
        for effect in self.status_effects:
            if effect.effect_type == effect_type:
                return effect
        return None

    def decrement_status_effects(self) -> None:
        """Decrement duration of all status effects and remove expired ones."""
        for effect in self.status_effects:
            effect.duration -= 1
        self.status_effects = [e for e in self.status_effects if e.duration > 0]

    def get_ac_modifier(self) -> int:
        """Calculate AC modifier from status effects (fortified/vulnerable)."""
        modifier = 0
        for effect in self.status_effects:
            if effect.effect_type == "fortified":
                modifier += effect.magnitude
            elif effect.effect_type == "vulnerable":
                modifier -= effect.magnitude
        return modifier

    def get_attack_modifier(self) -> int:
        """Calculate attack modifier from status effects (strengthened/weakened)."""
        modifier = self.attack_modifier
        for effect in self.status_effects:
            if effect.effect_type == "strengthened":
                modifier += effect.magnitude
            elif effect.effect_type == "weakened":
                modifier -= effect.magnitude
        return modifier

    def to_dict(self) -> dict:
        """Serialize entity to dictionary."""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "type": self.entity_type.value,
            "race": self.race,
            "class": self.char_class,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ac": self.ac,
            "attack_modifier": self.attack_modifier,
            "known_attacks": self.known_attacks,
            "spell_slots": {
                "current": self.spell_slots.current,
                "max": self.spell_slots.max,
            },
            "known_spells": self.known_spells,
            "status_effects": [
                {
                    "type": e.effect_type,
                    "duration": e.duration,
                    "magnitude": e.magnitude,
                    "source_id": e.source_id,
                }
                for e in self.status_effects
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """Deserialize entity from dictionary."""
        entity_type = EntityType(data["type"])
        spell_slots = SpellSlots(
            current=data["spell_slots"]["current"],
            max=data["spell_slots"]["max"],
        )
        status_effects = [
            StatusEffect(
                effect_type=e["type"],
                duration=e["duration"],
                magnitude=e.get("magnitude", 1),
                source_id=e.get("source_id"),
            )
            for e in data.get("status_effects", [])
        ]
        return cls(
            entity_id=data["entity_id"],
            name=data["name"],
            entity_type=entity_type,
            race=data["race"],
            char_class=data["class"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            ac=data["ac"],
            attack_modifier=data["attack_modifier"],
            known_attacks=data.get("known_attacks", []),
            spell_slots=spell_slots,
            known_spells=data.get("known_spells", []),
            status_effects=status_effects,
        )

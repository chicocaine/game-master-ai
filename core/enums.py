from enum import Enum

class StatusEffectType(Enum):
    ATKMOD = "attack_modifier"
    ACMOD = "ac_modifier"
    DOT = "DoT"
    HOT = "HoT"
    CONTROL = "control"
    IMMUNITY = "immunity"
    RESISTANCE = "resistance"
    VULNERABLE = "vulnerable" 

class DamageType(Enum):
    ACID = "acid"
    BLUDGEONING = "bludgeoning"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    PIERCING = "piercing"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    SLASHING = "slashing"
    THUNDER = "thunder"

class ControlType(Enum):
    STUNNED = "stunned"
    ASLEEP = "asleep"
    RESTRAINED = "restrained"
    SILENCED = "silenced"
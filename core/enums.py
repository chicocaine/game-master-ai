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

class AttackType(Enum):
    MELEE = "melee"
    RANGED = "ranged"
    UNARMED = "unarmed"
    AOE_MELEE = "aoe_melee"
    AOE_RANGED = "aoe_ranged"
    AOE_UNARMED = "aoe_unarmed"

class SpellType(Enum):
    ATTACK = "attack"
    HEAL = "heal"
    BUFF = "buff"
    DEBUFF = "debuff"
    CONTROL = "control"
    AOE_ATTACK = "aoe_attack"
    AOE_HEAL = "aoe_heal"
    AOE_BUFF = "aoe_buff"
    AOE_DEBUFF = "aoe_debuff"
    AOE_CONTROL = "aoe_control"
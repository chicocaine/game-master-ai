from enum import Enum

class GameState(Enum):
    PREGAME = "pregame"
    EXPLORATION = "exploration"
    ENCOUNTER = "encounter"
    POSTGAME = "postgame"

class DifficultyType(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class EventType(Enum):
    # lifecycle / system events
    GAME_STARTED = "game_started"
    GAME_FINISHED = "game_finished"
    GAME_STATE_CHANGED = "game_state_changed"
    TURN_STARTED = "turn_started"
    TURN_ENDED = "turn_ended"
    ROUND_STARTED = "round_started"
    ROUND_ENDED = "round_ended"

    # narration / communication events
    NARRATION = "narration"
    SYSTEM_MESSAGE = "system_message"
    PLAYER_MESSAGE = "player_message"
    ERROR = "error"

    # player action pipeline events
    ACTION_SUBMITTED = "action_submitted"
    ACTION_VALIDATED = "action_validated"
    ACTION_REJECTED = "action_rejected"
    ACTION_RESOLVED = "action_resolved"

    # pre-game / setup events
    PLAYER_CREATED = "player_created"
    PLAYER_REMOVED = "player_removed"
    DUNGEON_CHOSEN = "dungeon_chosen"

    # exploration / dungeon traversal events
    ROOM_ENTERED = "room_entered"
    ROOM_EXPLORED = "room_explored"
    MOVEMENT_RESOLVED = "movement_resolved"
    REST_STARTED = "rest_started"
    REST_COMPLETED = "rest_completed"

    # encounter / combat events
    ENCOUNTER_STARTED = "encounter_started"
    ENCOUNTER_ENDED = "encounter_ended"
    DICE_ROLLED = "dice_rolled"
    INITIATIVE_ROLLED = "initiative_rolled"
    ATTACK_DECLARED = "attack_declared"
    ATTACK_HIT = "attack_hit"
    ATTACK_MISSED = "attack_missed"
    DAMAGE_APPLIED = "damage_applied"
    SPELL_CAST = "spell_cast"
    HEALING_APPLIED = "healing_applied"
    STATUS_EFFECT_APPLIED = "status_effect_applied"
    STATUS_EFFECT_REMOVED = "status_effect_removed"
    STATUS_EFFECT_TICKED = "status_effect_ticked"
    DEATH = "death"
    REVIVE = "revive"

    # explicit game state update events
    HP_UPDATED = "hp_updated"
    MANA_UPDATED = "mana_updated"
    ENERGY_UPDATED = "energy_updated"
    COOLDOWNS_UPDATED = "cooldowns_updated"
    INVENTORY_UPDATED = "inventory_updated"
    POSITION_UPDATED = "position_updated"
    STATS_UPDATED = "stats_updated"
    REWARD_GRANTED = "reward_granted"
    PROGRESSION_UPDATED = "progression_updated"

class ActionType(Enum):
    # global actions (callable in every game mode)
    ABANDON = "abandon"
    QUERY = "query"
    CONVERSE = "converse"

    # exploration actions
    MOVE = "move"
    EXPLORE = "explore"
    REST = "rest"

    # encounter actions
    ATTACK = "attack"
    CAST_SPELL = "cast_spell"
    END_TURN = "end_turn" 

    # pre-game actions
    START = "start"
    CREATE_PLAYER = "create_player" # creates a player and adds to the party
    REMOVE_PLAYER = "remove_player" # removes a player from the party
    CHOOSE_DUNGEON = "choose_dungeon" # chooses a dungeon to play

    # post-game actions
    FINISH = "finish" # loops game state back to pre-game

class RestType(Enum):
    SHORT = "short"
    LONG = "long"

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

class WeaponProficiency(Enum):
    SIMPLE= "simple"
    MARTIAL = "martial"
    EXOTIC = "exotic"
    ARCANE = "arcane"
    DIVINE = "divine"
    TECH = "tech"

class WeaponHandling(Enum):
    ONE_HANDED = "one_handed"
    TWO_HANDED = "two_handed"
    VERSATILE = "versatile"

class WeaponWeightClass(Enum):
    LIGHT = "light"
    HEAVY = "heavy"

class WeaponDelivery(Enum):
    MELEE = "melee"
    RANGED = "ranged"
    VERSATILE = "versatile"

class WeaponMagicType(Enum):
    MUNDANE = "mundane"
    ENCHANTED = "enchanted"
    FOCUS = "focus"
    AUGMENT = "augment"
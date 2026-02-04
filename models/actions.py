"""Action models and definitions."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class ActionType(Enum):
    """Enumeration of action types."""
    MOVE = "move"
    ATTACK = "attack"
    CAST_SPELL = "cast_spell"
    REST = "rest"
    END_TURN = "end_turn"
    EXPLORE = "explore"


class RestType(Enum):
    """Types of rest available."""
    SHORT = "short"
    LONG = "long"


@dataclass
class Action:
    """Base action structure."""
    actor_id: str
    action_type: ActionType
    target_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize action to dictionary."""
        return {
            "actor_id": self.actor_id,
            "action_type": self.action_type.value,
            "target_id": self.target_id,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        """Deserialize action from dictionary."""
        return cls(
            actor_id=data["actor_id"],
            action_type=ActionType(data["action_type"]),
            target_id=data.get("target_id"),
            parameters=data.get("parameters", {}),
        )


@dataclass
class MoveAction(Action):
    """Action to move to a connected room."""
    def __init__(self, actor_id: str, target_room_id: str):
        super().__init__(
            actor_id=actor_id,
            action_type=ActionType.MOVE,
            target_id=target_room_id,
        )


@dataclass
class AttackAction(Action):
    """Action to attack a target."""
    def __init__(self, actor_id: str, target_entity_id: str, attack_id: str):
        super().__init__(
            actor_id=actor_id,
            action_type=ActionType.ATTACK,
            target_id=target_entity_id,
            parameters={"attack_id": attack_id},
        )


@dataclass
class CastSpellAction(Action):
    """Action to cast a spell."""
    def __init__(
        self,
        actor_id: str,
        spell_id: str,
        target_entity_id: Optional[str] = None,
    ):
        super().__init__(
            actor_id=actor_id,
            action_type=ActionType.CAST_SPELL,
            target_id=target_entity_id,
            parameters={"spell_id": spell_id},
        )


@dataclass
class RestAction(Action):
    """Action to rest and recover resources."""
    def __init__(self, actor_id: str, rest_type: RestType):
        super().__init__(
            actor_id=actor_id,
            action_type=ActionType.REST,
            parameters={"rest_type": rest_type.value},
        )


@dataclass
class EndTurnAction(Action):
    """Action to end current turn."""
    def __init__(self, actor_id: str):
        super().__init__(
            actor_id=actor_id,
            action_type=ActionType.END_TURN,
        )


@dataclass
class ExploreAction(Action):
    """Action to explore current room."""
    def __init__(self, actor_id: str):
        super().__init__(
            actor_id=actor_id,
            action_type=ActionType.EXPLORE,
        )

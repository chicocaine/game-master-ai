from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from core.enums import StatusEffectType, DamageType, ControlType

def _parse_effect_type(effect_type: Any) -> StatusEffectType:
    if isinstance(effect_type, StatusEffectType):
        return effect_type
    return StatusEffectType(str(effect_type))


def _get_parameters(data: dict) -> Dict[str, Any]:
    params = data.get("parameters", {})
    return dict(params) if isinstance(params, dict) else {}


def _get_str(data: dict, key: str) -> str:
    return str(data.get(key, ""))


def _get_int(value: Any) -> int:
    return int(value)


def _parse_damage_type(value: Any, default: DamageType = DamageType.FORCE) -> DamageType:
    if value in (None, ""):
        return default
    if isinstance(value, DamageType):
        return value
    return DamageType(str(value))


def _parse_control_type(value: Any) -> ControlType:
    if isinstance(value, ControlType):
        return value
    return ControlType(str(value))


def _get_duration(data: dict) -> Optional[int]:
    if "duration" in data:
        return _get_int(data.get("duration"))
    params = _get_parameters(data)
    return _get_int(params.get("duration"))

@dataclass
class StatusEffect:
    id: str
    name: str
    description: str
    type: StatusEffectType
    duration: int
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "duration": self.duration,
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StatusEffect":
        parsed_type = _parse_effect_type(data.get("type"))
        target_cls = _EFFECT_CLASS_BY_TYPE.get(parsed_type, cls)
        if target_cls is cls:
            return cls(
                id=_get_str(data, "id"),
                name=_get_str(data, "name"),
                description=_get_str(data, "description"),
                type=parsed_type,
                duration=_get_duration(data),
                parameters=_get_parameters(data),
            )
        return target_cls.from_dict(data)


@dataclass
class AtkModStatusEffect(StatusEffect):
    value: int = 0
    type: StatusEffectType = field(init=False, default=StatusEffectType.ATKMOD)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["parameters"] = {
            "value": self.value,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "AtkModStatusEffect":
        params = _get_parameters(data)
        return cls(
            id=_get_str(data, "id"),
            name=_get_str(data, "name"),
            description=_get_str(data, "description"),
            value=_get_int(params.get("value", 0)),
            duration=_get_duration(data),
        )


@dataclass
class ACModStatusEffect(StatusEffect):
    value: int = 0
    type: StatusEffectType = field(init=False, default=StatusEffectType.ACMOD)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["parameters"] = {
            "value": self.value,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ACModStatusEffect":
        params = _get_parameters(data)
        return cls(
            id=_get_str(data, "id"),
            name=_get_str(data, "name"),
            description=_get_str(data, "description"),
            value=_get_int(params.get("value", 0)),
            duration=_get_duration(data),
        )


@dataclass
class DoTStatusEffect(StatusEffect):
    value: int = 0
    damage_type: DamageType = DamageType.FORCE
    type: StatusEffectType = field(init=False, default=StatusEffectType.DOT)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["parameters"] = {
            "value": self.value,
            "damage_type": self.damage_type.value,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "DoTStatusEffect":
        params = _get_parameters(data)
        return cls(
            id=_get_str(data, "id"),
            name=_get_str(data, "name"),
            description=_get_str(data, "description"),
            value=_get_int(params.get("value", 0)),
            duration=_get_duration(data),
            damage_type=_parse_damage_type(data.get("damage_type", params.get("damage_type"))),
        )


@dataclass
class HoTStatusEffect(StatusEffect):
    value: int = 0
    type: StatusEffectType = field(init=False, default=StatusEffectType.HOT)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["parameters"] = {
            "value": self.value,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "HoTStatusEffect":
        params = _get_parameters(data)
        return cls(
            id=_get_str(data, "id"),
            name=_get_str(data, "name"),
            description=_get_str(data, "description"),
            value=_get_int(params.get("value", 0)),
            duration=_get_duration(data),
        )


@dataclass
class ControlStatusEffect(StatusEffect):
    control_type: ControlType = ControlType.STUNNED
    type: StatusEffectType = field(init=False, default=StatusEffectType.CONTROL)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["parameters"] = {
            "control_type": self.control_type.value,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "StatusEffect":
        params = _get_parameters(data)
        return cls(
            id=_get_str(data, "id"),
            name=_get_str(data, "name"),
            description=_get_str(data, "description"),
            control_type=_parse_control_type(params.get("control_type", "stunned")),
            duration=_get_duration(data),
        )


@dataclass
class ImmunityStatusEffect(StatusEffect):
    damage_type: DamageType = DamageType.FORCE
    type: StatusEffectType = field(init=False, default=StatusEffectType.IMMUNITY)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["parameters"] = {
            "damage_type": self.damage_type.value,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ImmunityStatusEffect":
        params = _get_parameters(data)
        return cls(
            id=_get_str(data, "id"),
            name=_get_str(data, "name"),
            description=_get_str(data, "description"),
            damage_type=_parse_damage_type(data.get("damage_type", params.get("damage_type"))),
            duration=_get_duration(data),
        )


@dataclass
class ResStatusEffect(StatusEffect):
    damage_type: DamageType = DamageType.FORCE
    type: StatusEffectType = field(init=False, default=StatusEffectType.RESISTANCE)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["parameters"] = {
            "damage_type": self.damage_type.value,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ResStatusEffect":
        params = _get_parameters(data)
        return cls(
            id=_get_str(data, "id"),
            name=_get_str(data, "name"),
            description=_get_str(data, "description"),
            damage_type=_parse_damage_type(data.get("damage_type", params.get("damage_type"))),
            duration=_get_duration(data),
        )


@dataclass
class VulnerableStatusEffect(StatusEffect):
    damage_type: DamageType = DamageType.FORCE
    type: StatusEffectType = field(init=False, default=StatusEffectType.VULNERABLE)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["parameters"] = {
            "damage_type": self.damage_type.value,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "VulnerableStatusEffect":
        params = _get_parameters(data)
        return cls(
            id=_get_str(data, "id"),
            name=_get_str(data, "name"),
            description=_get_str(data, "description"),
            damage_type=_parse_damage_type(data.get("damage_type", params.get("damage_type"))),
            duration=_get_duration(data),
        )


_EFFECT_CLASS_BY_TYPE = {
    StatusEffectType.ATKMOD: AtkModStatusEffect,
    StatusEffectType.ACMOD: ACModStatusEffect,
    StatusEffectType.DOT: DoTStatusEffect,
    StatusEffectType.HOT: HoTStatusEffect,
    StatusEffectType.CONTROL: ControlStatusEffect,
    StatusEffectType.IMMUNITY: ImmunityStatusEffect,
    StatusEffectType.RESISTANCE: ResStatusEffect,
    StatusEffectType.VULNERABLE: VulnerableStatusEffect,
}
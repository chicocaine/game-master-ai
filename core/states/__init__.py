from core.states.session import (
    EncounterStateData,
    ExplorationStateData,
    GameSessionState,
    PostGameStateData,
    PreGameStateData,
)


def validate_action_for_state(session, action):
    from core.states.manager import validate_action_for_state as _validate_action_for_state

    return _validate_action_for_state(session, action)


def apply_action(session, action):
    from core.states.manager import apply_action as _apply_action

    return _apply_action(session, action)


def build_postgame_summary(session):
    from core.states.postgame import build_postgame_summary as _build_postgame_summary

    return _build_postgame_summary(session)

__all__ = [
    "PreGameStateData",
    "ExplorationStateData",
    "EncounterStateData",
    "PostGameStateData",
    "GameSessionState",
    "validate_action_for_state",
    "apply_action",
    "build_postgame_summary",
]

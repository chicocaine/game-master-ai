from __future__ import annotations

from typing import Any, Dict, List

from core.events import Event
from core.resolution import (
    resolve_build_postgame_summary,
    resolve_finish_action,
)
from core.states.session import GameSessionState


def build_postgame_summary(session: GameSessionState) -> Dict[str, Any]:
    return resolve_build_postgame_summary(session)


def handle_finish(session: GameSessionState) -> List[Event]:
    return resolve_finish_action(session)

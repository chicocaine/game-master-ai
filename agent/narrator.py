from __future__ import annotations

from typing import List

from core.events import Event
from core.states.session import GameSessionState


class Narrator:
    def render(self, events: List[Event], session: GameSessionState) -> str:
        if not events:
            return ""

        event_names = ", ".join(event.name for event in events)
        return f"[{session.state.value}] {event_names}"

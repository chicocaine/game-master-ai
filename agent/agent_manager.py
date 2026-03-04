from __future__ import annotations

from typing import Any, Dict, List

from core.events import Event
from core.states.session import GameSessionState

from agent.context_builder import build_state_context
from agent.enemy_ai import EnemyAI
from agent.narrator import Narrator
from agent.player_parser import PlayerParser


class AgentManager:
    def __init__(
        self,
        player_parser: PlayerParser | None = None,
        narrator: Narrator | None = None,
        enemy_ai: EnemyAI | None = None,
    ) -> None:
        self.player_parser = player_parser or PlayerParser()
        self.narrator = narrator or Narrator()
        self.enemy_ai = enemy_ai or EnemyAI()

    def parse_player_input(self, raw_input: str, session: GameSessionState) -> Dict[str, Any]:
        return self.player_parser.parse(raw_input, session)

    def narrate_events(self, events: List[Event], session: GameSessionState) -> str:
        return self.narrator.render(events, session)

    def respond_conversation(self, message: str, session: GameSessionState) -> str:
        context = build_state_context(session)
        return f"[{context['state']}] {message.strip()}"

    def choose_enemy_action(self, session: GameSessionState, enemy_instance_id: str) -> Dict[str, Any]:
        return self.enemy_ai.choose_action(session, enemy_instance_id)

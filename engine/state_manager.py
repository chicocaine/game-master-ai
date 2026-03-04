from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from core.enums import GameState
from core.models.dungeon import Dungeon
from core.models.player import Player
from core.registry.dungeon_registry import load_dungeon_registry
from core.registry.player_registry import load_player_registry
from core.states.session import (
    EncounterStateData,
    ExplorationStateData,
    GameSessionState,
    PostGameStateData,
    PreGameStateData,
)


@dataclass(frozen=True)
class SessionTemplates:
    player_templates: Dict[str, Player]
    dungeon_templates: Dict[str, Dungeon]


class EngineStateManager:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self._templates: SessionTemplates | None = None

    def load_templates(self, force_reload: bool = False) -> SessionTemplates:
        if self._templates is not None and not force_reload:
            return self._templates

        player_templates = load_player_registry(self.data_dir)
        dungeon_templates = load_dungeon_registry(self.data_dir)
        self._templates = SessionTemplates(
            player_templates=player_templates,
            dungeon_templates=dungeon_templates,
        )
        return self._templates

    def create_session(self) -> GameSessionState:
        templates = self.load_templates()
        return GameSessionState(
            player_templates=templates.player_templates,
            dungeon_templates=templates.dungeon_templates,
        )

    def reset_session(self, session: GameSessionState) -> None:
        session.state = GameState.PREGAME
        session.party = []
        session.dungeon_id = ""
        session.dungeon = None
        session.turn = 0
        session.pregame = PreGameStateData(started=False)
        session.exploration = ExplorationStateData()
        session.encounter = EncounterStateData()
        session.postgame = PostGameStateData()

    def finalize_session(self, session: GameSessionState, outcome: str) -> None:
        from core.states.postgame import build_postgame_summary

        session.state = GameState.POSTGAME
        session.postgame.outcome = outcome
        session.postgame.summary = build_postgame_summary(session)

from __future__ import annotations

from typing import Any, Callable, Dict, List

from core.events import Event
from core.states.session import GameSessionState

from agent.context_builder import build_state_context
from agent.enemy_ai import EnemyAI
from agent.narration_batch import batch_events_for_narration
from agent.narrator import Narrator
from agent.prompt_loader import load_prompt
from agent.player_parser import PlayerParser
from agent.response_schema import validate_action_or_clarify, validate_enemy_action


JSONCompletionCallback = Callable[[str, str, str, Dict[str, Any]], Dict[str, Any]]
TextCompletionCallback = Callable[[str, str, str, Dict[str, Any]], str]


class AgentManager:
    def __init__(
        self,
        player_parser: PlayerParser | None = None,
        narrator: Narrator | None = None,
        enemy_ai: EnemyAI | None = None,
        json_completion: JSONCompletionCallback | None = None,
        text_completion: TextCompletionCallback | None = None,
    ) -> None:
        self.player_parser = player_parser or PlayerParser()
        self.narrator = narrator or Narrator()
        self.enemy_ai = enemy_ai or EnemyAI()
        self.json_completion = json_completion
        self.text_completion = text_completion

    def _has_json_completion(self) -> bool:
        return callable(self.json_completion)

    def _has_text_completion(self) -> bool:
        return callable(self.text_completion)

    def _llm_metadata(self, session: GameSessionState, role: str, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "role": role,
            "state": session.state.value,
            "turn": session.turn,
            "trace_id": str(getattr(session, "_active_trace_id", "")),
            "session_id": str(getattr(session, "_session_id", "")),
        }
        if extra:
            payload.update(extra)
        return payload

    def parse_player_input(self, raw_input: str, session: GameSessionState) -> Dict[str, Any]:
        if self._has_json_completion():
            context = build_state_context(session)
            system_prompt = load_prompt("action_parser")
            user_message = (
                "Context:\n"
                f"{context}\n\n"
                "Player Input:\n"
                f"{raw_input}"
            )
            try:
                payload = self.json_completion(
                    "action_parser",
                    system_prompt,
                    user_message,
                    self._llm_metadata(session, "action_parser", {"context_state": context.get("state", "")}),
                )
                if isinstance(payload, dict) and str(payload.get("type", "")).strip():
                    validate_action_or_clarify(payload)
                    return payload
            except Exception:
                pass
        return self.player_parser.parse(raw_input, session)

    def narrate_events(self, events: List[Event], session: GameSessionState) -> str:
        if self._has_text_completion():
            context = build_state_context(session)
            system_prompt = load_prompt("narration")
            batched_payload = batch_events_for_narration(events)
            user_message = (
                "Context:\n"
                f"{context}\n\n"
                "Batched Events:\n"
                f"{batched_payload}"
            )
            try:
                text = self.text_completion(
                    "narration",
                    system_prompt,
                    user_message,
                    self._llm_metadata(session, "narration", {"context_state": context.get("state", "")}),
                )
                return text.strip()
            except Exception:
                pass
        return self.narrator.render(events, session)

    def respond_conversation(self, message: str, session: GameSessionState) -> str:
        context = build_state_context(session)
        if self._has_text_completion():
            system_prompt = "You are a concise game master conversation assistant."
            user_message = (
                "Context:\n"
                f"{context}\n\n"
                "Player Message:\n"
                f"{message}"
            )
            try:
                text = self.text_completion(
                    "conversation",
                    system_prompt,
                    user_message,
                    self._llm_metadata(session, "conversation", {"context_state": context.get("state", "")}),
                )
                return text.strip()
            except Exception:
                pass
        return f"[{context['state']}] {message.strip()}"

    def choose_enemy_action(self, session: GameSessionState, enemy_instance_id: str) -> Dict[str, Any]:
        if self._has_json_completion():
            context = build_state_context(session)
            system_prompt = load_prompt("enemy_ai")
            user_message = (
                "Context:\n"
                f"{context}\n\n"
                "Acting Enemy:\n"
                f"{enemy_instance_id}"
            )
            try:
                payload = self.json_completion(
                    "enemy_ai",
                    system_prompt,
                    user_message,
                    self._llm_metadata(
                        session,
                        "enemy_ai",
                        {
                            "context_state": context.get("state", ""),
                            "enemy_instance_id": enemy_instance_id,
                        },
                    ),
                )
                if isinstance(payload, dict) and str(payload.get("type", "")).strip():
                    validate_enemy_action(payload)
                    return payload
            except Exception:
                pass
        return self.enemy_ai.choose_action(session, enemy_instance_id)

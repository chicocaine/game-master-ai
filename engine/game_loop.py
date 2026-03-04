from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.actions import Action, create_action
from core.enums import ActionType, EventType, GameState
from core.events import Event, create_event
from core.states.session import GameSessionState, get_active_encounter
from engine.game_state import apply_action


ParserCallback = Callable[[str, GameSessionState], Action | Dict[str, Any]]
NarrationCallback = Callable[[List[Event], GameSessionState], str]
EnemyActionCallback = Callable[[GameSessionState, str], Action | Dict[str, Any]]


@dataclass(frozen=True)
class LoopTurnResult:
    events: List[Event]
    narration: str = ""
    clarify: Optional[Dict[str, Any]] = None
    advanced_turn: bool = False


class GameLoop:
    def __init__(
        self,
        parser: ParserCallback,
        narrator: Optional[NarrationCallback] = None,
    ) -> None:
        self.parser = parser
        self.narrator = narrator
        self._pending_clarifications: Dict[int, Dict[str, Any]] = {}

    def run_turn(self, session: GameSessionState, raw_input: str) -> LoopTurnResult:
        session_key = id(session)
        pending = self._pending_clarifications.get(session_key)
        if pending is not None:
            resolved = self._resolve_pending_clarification(pending, raw_input)
            if resolved is None:
                return LoopTurnResult(
                    events=[],
                    narration=str(pending.get("question", "")).strip(),
                    clarify=pending,
                    advanced_turn=False,
                )
            parsed = resolved
            self._pending_clarifications.pop(session_key, None)
        else:
            parsed = self.parser(raw_input, session)

        if isinstance(parsed, dict) and str(parsed.get("type", "")).strip().lower() == "clarify":
            self._pending_clarifications[session_key] = parsed
            return LoopTurnResult(
                events=[],
                narration=str(parsed.get("question", "")).strip(),
                clarify=parsed,
                advanced_turn=False,
            )

        action = parsed if isinstance(parsed, Action) else Action.from_dict(parsed)
        previous_turn = session.turn
        events = apply_action(session, action)

        narration = ""
        if self.narrator is not None:
            narration = self.narrator(events, session)

        return LoopTurnResult(
            events=events,
            narration=narration,
            clarify=None,
            advanced_turn=session.turn > previous_turn,
        )

    def run_enemy_turn(self, session: GameSessionState, selector: EnemyActionCallback) -> LoopTurnResult:
        if session.state != GameState.ENCOUNTER:
            return LoopTurnResult(events=[], narration="", clarify=None, advanced_turn=False)

        encounter = get_active_encounter(session)
        if encounter is None:
            return LoopTurnResult(events=[], narration="", clarify=None, advanced_turn=False)
        if not session.encounter.turn_order:
            return LoopTurnResult(events=[], narration="", clarify=None, advanced_turn=False)
        if session.encounter.current_turn_index >= len(session.encounter.turn_order):
            return LoopTurnResult(events=[], narration="", clarify=None, advanced_turn=False)

        actor_instance_id = session.encounter.turn_order[session.encounter.current_turn_index]
        enemy_ids = {enemy.enemy_instance_id for enemy in encounter.enemies}
        if actor_instance_id not in enemy_ids:
            return LoopTurnResult(events=[], narration="", clarify=None, advanced_turn=False)

        pre_events: List[Event] = []
        try:
            parsed = selector(session, actor_instance_id)
            if isinstance(parsed, dict) and str(parsed.get("type", "")).strip().lower() == "clarify":
                pre_events.append(
                    create_event(
                        EventType.ACTION_REJECTED,
                        "action_rejected",
                        {
                            "errors": ["Enemy selector returned clarify; falling back to end_turn"],
                            "actor_instance_id": actor_instance_id,
                        },
                    )
                )
                action = self._fallback_end_turn_action(actor_instance_id)
            else:
                action = parsed if isinstance(parsed, Action) else Action.from_dict(parsed)
        except Exception as exc:
            pre_events.append(
                create_event(
                    EventType.ACTION_REJECTED,
                    "action_rejected",
                    {
                        "errors": [f"Enemy selector failed: {exc}"],
                        "actor_instance_id": actor_instance_id,
                    },
                )
            )
            action = self._fallback_end_turn_action(actor_instance_id)

        previous_turn = session.turn
        events = pre_events + apply_action(session, action)

        narration = ""
        if self.narrator is not None:
            narration = self.narrator(events, session)

        return LoopTurnResult(
            events=events,
            narration=narration,
            clarify=None,
            advanced_turn=session.turn > previous_turn,
        )

    def _resolve_pending_clarification(self, clarify_payload: Dict[str, Any], raw_input: str) -> Optional[Dict[str, Any]]:
        options = clarify_payload.get("options", [])
        if not isinstance(options, list) or not options:
            return None

        selected_value = self._resolve_option_selection(options, raw_input)
        if selected_value is None:
            return None

        template = clarify_payload.get("action_template")
        if not isinstance(template, dict):
            return None

        payload = dict(template)
        parameters = dict(payload.get("parameters", {}))
        ambiguous_field = str(clarify_payload.get("ambiguous_field", "")).strip()
        if ambiguous_field:
            if ambiguous_field.endswith("_ids"):
                parameters[ambiguous_field] = [selected_value]
            else:
                parameters[ambiguous_field] = selected_value
        payload["parameters"] = parameters
        return payload

    def _resolve_option_selection(self, options: List[Any], raw_input: str) -> Optional[str]:
        normalized_input = raw_input.strip()
        if not normalized_input:
            return None

        if normalized_input.isdigit():
            index = int(normalized_input) - 1
            if 0 <= index < len(options):
                option = options[index]
                if isinstance(option, dict):
                    return str(option.get("value", "")).strip() or None
                return str(option).strip() or None

        lookup = normalized_input.casefold()
        for option in options:
            if isinstance(option, dict):
                value = str(option.get("value", "")).strip()
                label = str(option.get("label", "")).strip()
                if value and value.casefold() == lookup:
                    return value
                if label and label.casefold() == lookup:
                    return value or label
            else:
                option_value = str(option).strip()
                if option_value and option_value.casefold() == lookup:
                    return option_value

        return None

    def _fallback_end_turn_action(self, actor_instance_id: str) -> Action:
        return create_action(
            action_type=ActionType.END_TURN,
            parameters={},
            actor_instance_id=actor_instance_id,
            reasoning="enemy_selector_fallback_end_turn",
            metadata={"source": "engine.game_loop"},
        )

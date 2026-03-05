from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

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
    action_type: str = ""
    actor_instance_id: str = ""
    turn_kind: str = "player"
    state: str = ""
    trace_id: str = ""
    parsed_action: Optional[Dict[str, Any]] = None


class GameLoop:
    def __init__(
        self,
        parser: ParserCallback,
        narrator: Optional[NarrationCallback] = None,
        runtime_logger: Any | None = None,
    ) -> None:
        self.parser = parser
        self.narrator = narrator
        self.runtime_logger = runtime_logger
        self._pending_clarifications: Dict[int, Dict[str, Any]] = {}

    def run_turn(self, session: GameSessionState, raw_input: str) -> LoopTurnResult:
        trace_id = str(uuid4())
        self._set_active_trace_id(session, trace_id)
        try:
            return self._run_turn_with_trace(session, raw_input, trace_id)
        finally:
            self._clear_active_trace_id(session)

    def _run_turn_with_trace(self, session: GameSessionState, raw_input: str, trace_id: str) -> LoopTurnResult:
        previous_turn = session.turn
        session_key = id(session)

        pending = self._pending_clarifications.get(session_key)
        if pending is not None:
            resolved = self._resolve_pending_clarification(pending, raw_input)
            if resolved is None:
                result = LoopTurnResult(
                    events=[],
                    narration=str(pending.get("question", "")).strip(),
                    clarify=pending,
                    advanced_turn=False,
                    action_type="clarify",
                    actor_instance_id="",
                    turn_kind="player",
                    state=session.state.value,
                    trace_id=trace_id,
                    parsed_action={"type": "clarify_pending"},
                )
                self._log_runtime_turn(
                    turn_kind="player",
                    session=session,
                    raw_input=raw_input,
                    result=result,
                    parsed={"type": "clarify_pending"},
                    turn_before=previous_turn,
                    trace_id=trace_id,
                )
                return result
            parsed = resolved
            self._pending_clarifications.pop(session_key, None)
        else:
            try:
                parsed = self.parser(raw_input, session)
            except Exception as exc:
                events = [
                    create_event(
                        EventType.ACTION_REJECTED,
                        "action_rejected",
                        {"errors": [f"Parser failed: {exc}"]},
                    )
                ]
                narration = ""
                if self.narrator is not None:
                    narration = self.narrator(events, session)
                result = LoopTurnResult(
                    events=events,
                    narration=narration,
                    clarify=None,
                    advanced_turn=False,
                    action_type="parser_error",
                    actor_instance_id="",
                    turn_kind="player",
                    state=session.state.value,
                    trace_id=trace_id,
                    parsed_action={"type": "parser_error", "error": str(exc)},
                )
                self._log_runtime_turn(
                    turn_kind="player",
                    session=session,
                    raw_input=raw_input,
                    result=result,
                    parsed={"type": "parser_error", "error": str(exc)},
                    turn_before=previous_turn,
                    parser_failed=True,
                    trace_id=trace_id,
                )
                return result

        if isinstance(parsed, dict) and str(parsed.get("type", "")).strip().lower() == "clarify":
            self._pending_clarifications[session_key] = parsed
            result = LoopTurnResult(
                events=[],
                narration=str(parsed.get("question", "")).strip(),
                clarify=parsed,
                advanced_turn=False,
                action_type="clarify",
                actor_instance_id=str(parsed.get("actor_instance_id", "")) if isinstance(parsed, dict) else "",
                turn_kind="player",
                state=session.state.value,
                trace_id=trace_id,
                parsed_action=parsed,
            )
            self._log_runtime_turn(
                turn_kind="player",
                session=session,
                raw_input=raw_input,
                result=result,
                parsed=parsed,
                turn_before=previous_turn,
                trace_id=trace_id,
            )
            return result

        action = parsed if isinstance(parsed, Action) else Action.from_dict(parsed)
        events = apply_action(session, action)

        narration = ""
        if self.narrator is not None:
            narration = self.narrator(events, session)

        result = LoopTurnResult(
            events=events,
            narration=narration,
            clarify=None,
            advanced_turn=session.turn > previous_turn,
            action_type=action.type.value,
            actor_instance_id=action.actor_instance_id,
            turn_kind="player",
            state=session.state.value,
            trace_id=trace_id,
            parsed_action=action.to_dict(),
        )
        self._log_runtime_turn(
            turn_kind="player",
            session=session,
            raw_input=raw_input,
            result=result,
            parsed=action,
            turn_before=previous_turn,
            trace_id=trace_id,
        )
        return result

    def run_enemy_turn(self, session: GameSessionState, selector: EnemyActionCallback) -> LoopTurnResult:
        trace_id = str(uuid4())
        self._set_active_trace_id(session, trace_id)
        try:
            return self._run_enemy_turn_with_trace(session, selector, trace_id)
        finally:
            self._clear_active_trace_id(session)

    def _run_enemy_turn_with_trace(
        self,
        session: GameSessionState,
        selector: EnemyActionCallback,
        trace_id: str,
    ) -> LoopTurnResult:
        if session.state != GameState.ENCOUNTER:
            return LoopTurnResult(
                events=[],
                narration="",
                clarify=None,
                advanced_turn=False,
                action_type="",
                actor_instance_id="",
                turn_kind="enemy",
                state=session.state.value,
                trace_id=trace_id,
                parsed_action=None,
            )

        encounter = get_active_encounter(session)
        if encounter is None:
            return LoopTurnResult(
                events=[],
                narration="",
                clarify=None,
                advanced_turn=False,
                action_type="",
                actor_instance_id="",
                turn_kind="enemy",
                state=session.state.value,
                trace_id=trace_id,
                parsed_action=None,
            )
        if not session.encounter.turn_order:
            return LoopTurnResult(
                events=[],
                narration="",
                clarify=None,
                advanced_turn=False,
                action_type="",
                actor_instance_id="",
                turn_kind="enemy",
                state=session.state.value,
                trace_id=trace_id,
                parsed_action=None,
            )
        if session.encounter.current_turn_index >= len(session.encounter.turn_order):
            return LoopTurnResult(
                events=[],
                narration="",
                clarify=None,
                advanced_turn=False,
                action_type="",
                actor_instance_id="",
                turn_kind="enemy",
                state=session.state.value,
                trace_id=trace_id,
                parsed_action=None,
            )

        actor_instance_id = session.encounter.turn_order[session.encounter.current_turn_index]
        enemy_ids = {enemy.enemy_instance_id for enemy in encounter.enemies}
        if actor_instance_id not in enemy_ids:
            return LoopTurnResult(
                events=[],
                narration="",
                clarify=None,
                advanced_turn=False,
                action_type="",
                actor_instance_id=actor_instance_id,
                turn_kind="enemy",
                state=session.state.value,
                trace_id=trace_id,
                parsed_action=None,
            )

        pre_events: List[Event] = []
        selector_failed = False
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
            selector_failed = True
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

        result = LoopTurnResult(
            events=events,
            narration=narration,
            clarify=None,
            advanced_turn=session.turn > previous_turn,
            action_type=action.type.value,
            actor_instance_id=action.actor_instance_id,
            turn_kind="enemy",
            state=session.state.value,
            trace_id=trace_id,
            parsed_action=action.to_dict(),
        )
        self._log_runtime_turn(
            turn_kind="enemy",
            session=session,
            raw_input=f"enemy:{actor_instance_id}",
            result=result,
            parsed=action,
            turn_before=previous_turn,
            parser_failed=selector_failed,
            trace_id=trace_id,
        )
        return result

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

    def _log_runtime_turn(
        self,
        *,
        turn_kind: str,
        session: GameSessionState,
        raw_input: str,
        result: LoopTurnResult,
        parsed: Any,
        turn_before: int,
        parser_failed: bool = False,
        trace_id: str = "",
    ) -> None:
        if self.runtime_logger is None or not hasattr(self.runtime_logger, "log_turn"):
            return

        validation_failed = any(event.type == EventType.ACTION_REJECTED for event in result.events) and not parser_failed
        parsed_payload = parsed.to_dict() if isinstance(parsed, Action) else parsed

        self.runtime_logger.log_turn(
            {
                "trace_id": trace_id,
                "turn_kind": turn_kind,
                "state": session.state.value,
                "turn_before": turn_before,
                "turn_after": session.turn,
                "raw_input": raw_input,
                "advanced_turn": result.advanced_turn,
                "clarify": result.clarify,
                "parser_failed": parser_failed,
                "validation_failed": validation_failed,
                "parsed": parsed_payload,
                "events": [event.to_dict() for event in result.events],
                "narration": result.narration,
            }
        )

    def _set_active_trace_id(self, session: GameSessionState, trace_id: str) -> None:
        setattr(session, "_active_trace_id", trace_id)

    def _clear_active_trace_id(self, session: GameSessionState) -> None:
        if hasattr(session, "_active_trace_id"):
            delattr(session, "_active_trace_id")

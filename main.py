from __future__ import annotations

import argparse
from typing import Any, Callable, Dict, Tuple
from uuid import uuid4

from agent.agent_manager import AgentManager
from core.enums import GameState
from core.states.session import find_player_by_instance_id, get_active_encounter
from engine.config import load_llm_settings
from engine.game_loop import GameLoop, LoopTurnResult
from engine.llm_client import LLMClient, LLMError, LLMRequest
from engine.llm_transports import build_transport
from engine.runtime_logger import RuntimeTurnLogger
from engine.state_manager import EngineStateManager


JSONCompletionCallback = Callable[[str, str, str, Dict[str, Any]], Dict[str, Any]]
TextCompletionCallback = Callable[[str, str, str, Dict[str, Any]], str]


def _build_llm_callbacks(enable_live_llm: bool) -> Tuple[JSONCompletionCallback | None, TextCompletionCallback | None, str]:
	if not enable_live_llm:
		return None, None, "live LLM disabled (using deterministic local agent)"

	settings = load_llm_settings()
	if not settings.api_key:
		return None, None, "LLM_API_KEY missing; falling back to deterministic local agent"

	try:
		transport = build_transport(settings)
	except Exception as exc:
		return None, None, f"failed to initialize LLM transport ({exc}); falling back to deterministic local agent"

	llm_client = LLMClient(transport=transport)

	def _role_temperature(role: str) -> float:
		if role == "action_parser":
			return settings.action_temperature
		if role == "enemy_ai":
			return settings.enemy_temperature
		if role == "narration":
			return settings.narration_temperature
		if role == "conversation":
			return settings.conversation_temperature
		return settings.temperature

	def _role_max_tokens(role: str) -> int:
		if role == "action_parser":
			return settings.action_max_tokens
		if role == "enemy_ai":
			return settings.enemy_max_tokens
		if role == "narration":
			return settings.narration_max_tokens
		if role == "conversation":
			return settings.conversation_max_tokens
		return settings.max_tokens

	def _json_completion(role: str, system_prompt: str, user_message: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
		request = LLMRequest(
			role=role,
			system_prompt=system_prompt,
			user_message=user_message,
			model=settings.model,
			max_tokens=_role_max_tokens(role),
			temperature=_role_temperature(role),
			metadata=metadata,
		)
		response = llm_client.complete(request, parse_json=True)
		payload = response.get("parsed")
		if not isinstance(payload, dict):
			raise LLMError("Expected a JSON object payload")
		metadata_payload = payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {}
		payload["metadata"] = {
			**metadata_payload,
			"llm_request_id": response.get("request_id", ""),
		}
		return payload

	def _text_completion(role: str, system_prompt: str, user_message: str, metadata: Dict[str, Any]) -> str:
		request = LLMRequest(
			role=role,
			system_prompt=system_prompt,
			user_message=user_message,
			model=settings.model,
			max_tokens=_role_max_tokens(role),
			temperature=_role_temperature(role),
			metadata=metadata,
		)
		response = llm_client.complete(request, parse_json=False)
		return str(response.get("text", ""))

	mode_label = f"live LLM enabled via provider='{settings.provider}' model='{settings.model}'"
	return _json_completion, _text_completion, mode_label


def _is_enemy_turn(session) -> bool:
	if session.state != GameState.ENCOUNTER:
		return False

	encounter = get_active_encounter(session)
	if encounter is None:
		return False

	turn_order = session.encounter.turn_order
	if not turn_order:
		return False

	idx = session.encounter.current_turn_index
	if idx < 0 or idx >= len(turn_order):
		return False

	actor_id = turn_order[idx]
	return find_player_by_instance_id(session, actor_id) is None


def _render_turn_result(result: LoopTurnResult) -> None:
	if result.clarify:
		print(f"\nClarify: {result.clarify.get('question', '').strip()}")
		options = result.clarify.get("options", [])
		for index, option in enumerate(options, start=1):
			if isinstance(option, dict):
				label = str(option.get("label", option.get("value", ""))).strip()
			else:
				label = str(option).strip()
			if label:
				print(f"  {index}) {label}")
		return

	if result.narration.strip():
		print(f"\n{result.narration.strip()}")
	elif result.events:
		print("\nEvents:")
		for event in result.events:
			print(f"- {event.name}")
	else:
		print("\n(no output)")


def run_cli(enable_live_llm: bool) -> None:
	session_id = f"sess_{uuid4().hex[:8]}"
	state_manager = EngineStateManager("data")
	session = state_manager.create_session()
	setattr(session, "_session_id", session_id)

	json_completion, text_completion, mode_label = _build_llm_callbacks(enable_live_llm)
	agent = AgentManager(json_completion=json_completion, text_completion=text_completion)

	runtime_logger = RuntimeTurnLogger(session_id)
	loop = GameLoop(
		parser=agent.parse_player_input,
		narrator=agent.narrate_events,
		runtime_logger=runtime_logger,
	)

	print("Game Master AI CLI")
	print(mode_label)
	print("Type 'quit' or 'exit' to stop. Input can be natural language or action JSON.")

	while True:
		try:
			raw = input("\n> ").strip()
		except EOFError:
			print("\nExiting.")
			break

		if not raw:
			continue

		if raw.casefold() in {"quit", "exit"}:
			print("Exiting.")
			break

		result = loop.run_turn(session, raw)
		_render_turn_result(result)

		while _is_enemy_turn(session):
			enemy_result = loop.run_enemy_turn(session, agent.choose_enemy_action)
			_render_turn_result(enemy_result)
			if enemy_result.clarify is not None:
				break


def main() -> None:
	parser = argparse.ArgumentParser(description="Run Game Master AI CLI loop")
	parser.add_argument(
		"--live-llm",
		action="store_true",
		help="Enable live LLM calls using .env configuration",
	)
	args = parser.parse_args()
	run_cli(enable_live_llm=args.live_llm)


if __name__ == "__main__":
	main()

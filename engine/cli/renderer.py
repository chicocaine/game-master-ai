from __future__ import annotations

from typing import Any, Dict

from engine.game_loop import LoopTurnResult


def render_startup(mode_label: str) -> None:
    print("[game-master-ai][cli] Game Master AI CLI")
    print(f"[game-master-ai][mode] {mode_label}")
    print("[game-master-ai][hint] Type 'quit' or 'exit' to stop. Input can be natural language or action JSON.")


def render_turn_result(result: LoopTurnResult) -> None:
    _render_debug_block(result)

    if result.clarify:
        print(f"\n[game-master-ai][clarify] {str(result.clarify.get('question', '')).strip()}")
        options = result.clarify.get("options", []) if isinstance(result.clarify, dict) else []
        for index, option in enumerate(options, start=1):
            if isinstance(option, dict):
                label = str(option.get("label", option.get("value", ""))).strip()
            else:
                label = str(option).strip()
            if label:
                print(f"  [{index}] {label}")
        return

    if result.narration.strip():
        print(f"\n[game-master-ai][narration] {result.narration.strip()}")
    elif result.events:
        print("\n[game-master-ai][events]")
        for event in result.events:
            print(f"- {event.name}")
    else:
        print("\n[game-master-ai][events] (no output)")


def _render_debug_block(result: LoopTurnResult) -> None:
    print("\n[debug][turn]")
    print(f"- kind: {result.turn_kind}")
    print(f"- state: {result.state}")
    print(f"- trace_id: {result.trace_id}")
    print(f"- action_type: {result.action_type}")
    print(f"- actor_instance_id: {result.actor_instance_id}")
    print(f"- advanced_turn: {result.advanced_turn}")
    print(f"- event_count: {len(result.events)}")
    print(f"- parsed_action: {_compact_dict(result.parsed_action)}")


def _compact_dict(value: Dict[str, Any] | None) -> str:
    if not value:
        return "{}"
    keys = ["type", "actor_instance_id", "parameters", "reasoning", "metadata"]
    compact = {key: value.get(key) for key in keys if key in value}
    return str(compact)

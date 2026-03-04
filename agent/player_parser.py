from __future__ import annotations

import json
from typing import Any, Dict

from core.enums import GameState
from core.states.session import find_player_by_instance_id, get_active_encounter
from core.states.session import GameSessionState

from agent.context_builder import build_state_context


class PlayerParser:
    def parse(self, raw_input: str, session: GameSessionState) -> Dict[str, Any]:
        _ = build_state_context(session)

        normalized_input = raw_input.strip()
        if not normalized_input:
            return {
                "type": "clarify",
                "ambiguous_field": "input",
                "question": "I need a bit more detail. What action do you want to take?",
                "options": [],
            }

        try:
            payload = json.loads(normalized_input)
            if isinstance(payload, dict) and str(payload.get("type", "")).strip():
                return payload
        except json.JSONDecodeError:
            pass

        attack_clarify = self._build_attack_clarify(normalized_input, session)
        if attack_clarify is not None:
            return attack_clarify

        return {
            "type": "query",
            "parameters": {"question": normalized_input},
            "raw_input": raw_input,
            "reasoning": "fallback_query_for_unparsed_input",
            "metadata": {"source": "agent.player_parser"},
        }

    def _build_attack_clarify(self, normalized_input: str, session: GameSessionState) -> Dict[str, Any] | None:
        if normalized_input.casefold() not in {"attack", "hit", "strike"}:
            return None
        if session.state != GameState.ENCOUNTER:
            return None

        encounter = get_active_encounter(session)
        if encounter is None:
            return None

        alive_enemies = [enemy for enemy in encounter.enemies if enemy.hp > 0]
        if len(alive_enemies) <= 1:
            return None

        actor_instance_id = ""
        if session.encounter.turn_order and session.encounter.current_turn_index < len(session.encounter.turn_order):
            candidate_actor_id = session.encounter.turn_order[session.encounter.current_turn_index]
            actor = find_player_by_instance_id(session, candidate_actor_id)
            if actor is not None and actor.merged_attacks:
                actor_instance_id = actor.player_instance_id
                return {
                    "type": "clarify",
                    "ambiguous_field": "target_instance_ids",
                    "question": "Who do you want to target?",
                    "options": [
                        {
                            "label": f"{enemy.name} ({enemy.enemy_instance_id})",
                            "value": enemy.enemy_instance_id,
                        }
                        for enemy in alive_enemies
                    ],
                    "action_template": {
                        "type": "attack",
                        "actor_instance_id": actor_instance_id,
                        "parameters": {"attack_id": actor.merged_attacks[0].id},
                        "raw_input": normalized_input,
                        "reasoning": "clarify_target_for_attack",
                        "metadata": {"source": "agent.player_parser"},
                    },
                }

        return None

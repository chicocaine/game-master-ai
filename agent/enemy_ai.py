from __future__ import annotations

from typing import Any, Dict

from core.states.session import GameSessionState, alive_players, get_active_encounter


class EnemyAI:
    def choose_action(self, session: GameSessionState, enemy_instance_id: str) -> Dict[str, Any]:
        encounter = get_active_encounter(session)
        if encounter is None:
            return {
                "type": "query",
                "parameters": {"question": "No active encounter for enemy action."},
                "actor_instance_id": enemy_instance_id,
            }

        enemy = next(
            (item for item in encounter.enemies if item.enemy_instance_id == enemy_instance_id),
            None,
        )
        if enemy is None:
            return {
                "type": "query",
                "parameters": {"question": f"Unknown enemy '{enemy_instance_id}'"},
                "actor_instance_id": enemy_instance_id,
            }

        living_players = alive_players(session.party)
        if enemy.merged_attacks and living_players:
            return {
                "type": "attack",
                "actor_instance_id": enemy_instance_id,
                "parameters": {
                    "attack_id": enemy.merged_attacks[0].id,
                    "target_instance_ids": [living_players[0].player_instance_id],
                },
                "reasoning": "fallback_enemy_action_lowest_index_alive_player",
                "metadata": {"source": "agent.enemy_ai"},
            }

        return {
            "type": "end_turn",
            "actor_instance_id": enemy_instance_id,
            "parameters": {},
            "reasoning": "fallback_enemy_action_end_turn",
            "metadata": {"source": "agent.enemy_ai"},
        }

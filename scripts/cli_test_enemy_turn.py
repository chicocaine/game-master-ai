from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.agent_manager import AgentManager
from core.enums import DifficultyType, GameState
from core.models.dungeon import Dungeon, Encounter, Room
from core.models.enemy import Enemy
from core.registry.enemy_registry import load_enemy_model_registry
from engine.game_loop import GameLoop
from engine.state_manager import EngineStateManager


def _build_enemy_turn_session():
    manager = EngineStateManager("data")
    session = manager.create_session()

    player_template = next(iter(session.player_templates.values()))
    player_template.player_instance_id = "plr_inst_cli_enemy_01"
    session.party = [player_template]

    enemy_template = next(iter(load_enemy_model_registry("data").values()))
    enemy = Enemy.from_dict(enemy_template.to_dict())
    enemy.enemy_instance_id = "enm_inst_cli_enemy_01"

    room = Room(
        id="room_cli_enemy",
        name="CLI Enemy Room",
        description="room",
        is_visited=True,
        is_cleared=False,
        is_rested=False,
        connections=[],
        encounters=[
            Encounter(
                id="enc_cli_enemy_01",
                name="CLI Enemy Encounter",
                description="enc",
                difficulty=DifficultyType.EASY,
                cleared=False,
                clear_reward=1,
                enemies=[enemy],
            )
        ],
        allowed_rests=[],
    )
    session.dungeon = Dungeon(
        id="dgn_cli_enemy",
        name="CLI Enemy Dungeon",
        description="dgn",
        difficulty=DifficultyType.EASY,
        start_room=room.id,
        end_room=room.id,
        rooms=[room],
    )
    session.dungeon_id = session.dungeon.id
    session.state = GameState.ENCOUNTER
    session.exploration.current_room_id = room.id
    session.encounter.active_encounter_id = "enc_cli_enemy_01"
    session.encounter.turn_order = [enemy.enemy_instance_id, player_template.player_instance_id]
    session.encounter.current_turn_index = 0

    return session, enemy.enemy_instance_id


def main() -> None:
    session, enemy_id = _build_enemy_turn_session()
    manager = AgentManager()
    loop = GameLoop(parser=manager.parse_player_input)

    legal_result = loop.run_enemy_turn(session, manager.choose_enemy_action)
    legal_enemy_turn_ok = legal_result.advanced_turn is True and len(legal_result.events) > 0

    fallback_session, _enemy_id = _build_enemy_turn_session()
    fallback_result = loop.run_enemy_turn(
        fallback_session,
        selector=lambda _session, _actor_id: (_ for _ in ()).throw(RuntimeError("forced failure")),
    )
    fallback_has_rejection = any(event.name == "action_rejected" for event in fallback_result.events)
    fallback_has_turn_end = any(event.name == "turn_ended" for event in fallback_result.events)

    print("Enemy Turn Runtime Test")
    print(f"- enemy_id: {enemy_id}")
    print(f"- legal_enemy_turn_ok: {legal_enemy_turn_ok}")
    print(f"- fallback_has_rejection: {fallback_has_rejection}")
    print(f"- fallback_has_turn_end: {fallback_has_turn_end}")

    if not (legal_enemy_turn_ok and fallback_has_rejection and fallback_has_turn_end):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Session logging for replay and analysis."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from models.states import GlobalGameState, EncounterState


class SessionLogger:
    """Logs game session events for replay and analysis."""

    def __init__(self, session_id: str, logs_dir: str = "logs/sessions"):
        """Initialize session logger."""
        self.session_id = session_id
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.timestamp_start = datetime.utcnow()
        self.events: List[Dict[str, Any]] = []

    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log a game event."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "details": details,
        }
        self.events.append(event)

    def log_action_initiated(
        self,
        actor_id: str,
        raw_input: str,
        parsed_intent: str,
        confidence: float,
        action: Dict[str, Any],
    ) -> None:
        """Log when a player action is initiated."""
        self.log_event(
            "action_initiated",
            {
                "actor_id": actor_id,
                "raw_input": raw_input,
                "parsed_intent": parsed_intent,
                "confidence": confidence,
                "action": action,
            },
        )

    def log_combat_started(
        self,
        encounter_id: str,
        room_id: str,
        initiative_order: List[str],
        entities: List[Dict[str, Any]],
    ) -> None:
        """Log when combat begins."""
        self.log_event(
            "combat_started",
            {
                "encounter_id": encounter_id,
                "room_id": room_id,
                "initiative_order": initiative_order,
                "entities": entities,
            },
        )

    def log_action_resolved(
        self,
        actor_id: str,
        action_type: str,
        round_num: int,
        details: Dict[str, Any],
        narration: str,
    ) -> None:
        """Log when an action is resolved."""
        self.log_event(
            "action_resolved",
            {
                "actor_id": actor_id,
                "action_type": action_type,
                "round": round_num,
                "details": details,
                "narration": narration,
            },
        )

    def log_status_effect_applied(
        self,
        entity_id: str,
        effect_type: str,
        duration: int,
        magnitude: int,
        source_id: Optional[str] = None,
    ) -> None:
        """Log when a status effect is applied."""
        self.log_event(
            "status_effect_applied",
            {
                "entity_id": entity_id,
                "effect_type": effect_type,
                "duration": duration,
                "magnitude": magnitude,
                "source_id": source_id,
            },
        )

    def log_status_effect_triggered(
        self,
        entity_id: str,
        effect_type: str,
        damage_applied: int,
        duration_remaining: int,
    ) -> None:
        """Log when a status effect triggers."""
        self.log_event(
            "status_effect_triggered",
            {
                "entity_id": entity_id,
                "effect_type": effect_type,
                "damage_applied": damage_applied,
                "duration_remaining": duration_remaining,
            },
        )

    def log_entity_died(
        self,
        entity_id: str,
        name: str,
        final_hp: int,
        killed_by: Optional[str] = None,
    ) -> None:
        """Log when an entity dies."""
        self.log_event(
            "entity_died",
            {
                "entity_id": entity_id,
                "name": name,
                "final_hp": final_hp,
                "killed_by": killed_by,
            },
        )

    def log_encounter_ended(
        self,
        encounter_id: str,
        result: str,  # "victory" or "defeat"
        reward: int,
        player_states: List[Dict[str, Any]],
    ) -> None:
        """Log when an encounter ends."""
        self.log_event(
            "encounter_ended",
            {
                "encounter_id": encounter_id,
                "result": result,
                "reward": reward,
                "player_final_states": player_states,
            },
        )

    def log_exploration_moved(
        self,
        from_room: str,
        to_room: str,
        room_description: str,
    ) -> None:
        """Log when party moves to a new room."""
        self.log_event(
            "exploration_moved",
            {
                "from_room": from_room,
                "to_room": to_room,
                "room_description": room_description,
            },
        )

    def log_rest_completed(
        self,
        rest_type: str,
        room_id: str,
        player_states: List[Dict[str, Any]],
    ) -> None:
        """Log when party rests."""
        self.log_event(
            "rest_completed",
            {
                "rest_type": rest_type,
                "room_id": room_id,
                "player_states_after": player_states,
            },
        )

    def log_game_ended(
        self,
        result: str,  # "GAME_COMPLETE", "GAME_OVER", "ABANDONED"
        total_rewards: int,
        total_encounters: int,
        final_party_state: List[Dict[str, Any]],
    ) -> None:
        """Log when game ends."""
        self.log_event(
            "game_ended",
            {
                "result": result,
                "total_rewards": total_rewards,
                "total_encounters": total_encounters,
                "final_party_state": final_party_state,
            },
        )

    def save(self, dungeon_id: str, result: str) -> Path:
        """Save session log to file."""
        session_data = {
            "session_id": self.session_id,
            "timestamp_start": self.timestamp_start.isoformat() + "Z",
            "timestamp_end": datetime.utcnow().isoformat() + "Z",
            "dungeon_id": dungeon_id,
            "result": result,
            "events": self.events,
        }

        filename = f"session_{self.session_id}.json"
        filepath = self.logs_dir / filename

        with open(filepath, "w") as f:
            json.dump(session_data, f, indent=2)

        print(f"Session log saved: {filepath}")
        return filepath

    @staticmethod
    def load(session_id: str, logs_dir: str = "logs/sessions") -> Optional[Dict[str, Any]]:
        """Load a session log from file."""
        logs_path = Path(logs_dir)
        filepath = logs_path / f"session_{session_id}.json"

        if not filepath.exists():
            return None

        with open(filepath, "r") as f:
            return json.load(f)

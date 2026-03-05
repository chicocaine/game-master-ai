from __future__ import annotations

from typing import Any, Dict, List

from core.events import Event


def batch_events_for_narration(events: List[Event]) -> Dict[str, Any]:
    serialized = [event.to_dict() for event in events]
    beats = _build_beats(serialized)
    return {
        "event_count": len(serialized),
        "events": serialized,
        "beats": beats,
    }


def _build_beats(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    beats: List[Dict[str, Any]] = []
    for event in events:
        event_type = str(event.get("type", "")).strip()
        payload = event.get("payload", {}) if isinstance(event.get("payload", {}), dict) else {}
        actor = str(payload.get("actor_instance_id") or payload.get("attacker_id") or payload.get("source_id") or "")
        target = str(payload.get("target_instance_id") or payload.get("target_id") or "")
        beat_key = f"{event_type}|{actor}|{target}"

        if beats and beats[-1].get("beat_key") == beat_key:
            beats[-1]["events"].append(event)
            continue

        beats.append(
            {
                "beat_key": beat_key,
                "event_type": event_type,
                "actor_instance_id": actor,
                "target_instance_id": target,
                "events": [event],
            }
        )

    for beat in beats:
        beat.pop("beat_key", None)

    return beats

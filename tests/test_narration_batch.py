from core.enums import EventType
from core.events import create_event
from agent.narration_batch import batch_events_for_narration


def test_batch_events_for_narration_groups_related_events_into_beats():
    events = [
        create_event(EventType.ATTACK_DECLARED, "attack_declared", {"actor_instance_id": "plr_01", "target_id": "enm_01"}),
        create_event(EventType.ATTACK_HIT, "attack_hit", {"actor_instance_id": "plr_01", "target_id": "enm_01"}),
        create_event(EventType.DAMAGE_APPLIED, "damage_applied", {"actor_instance_id": "plr_01", "target_id": "enm_01"}),
        create_event(EventType.TURN_ENDED, "turn_ended", {"actor_instance_id": "plr_01"}),
    ]

    payload = batch_events_for_narration(events)

    assert payload["event_count"] == 4
    assert len(payload["beats"]) >= 2
    assert payload["beats"][0]["event_type"] == "attack_declared"
    assert len(payload["beats"][0]["events"]) >= 1

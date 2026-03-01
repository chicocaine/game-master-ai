from core.enums import EventType
from core.events import Event, create_event


def test_event_type_includes_dice_and_initiative_rolls():
    assert EventType.DICE_ROLLED.value == "dice_rolled"
    assert EventType.INITIATIVE_ROLLED.value == "initiative_rolled"


def test_create_event_sets_type_name_payload_and_source():
    event = create_event(
        event_type=EventType.ATTACK_HIT,
        name="player_attack_hit",
        payload={"attacker_id": "plr_01", "target_id": "enm_01", "damage": 7},
        source="combat_engine",
    )

    assert event.type == EventType.ATTACK_HIT
    assert event.name == "player_attack_hit"
    assert event.payload["damage"] == 7
    assert event.source == "combat_engine"
    assert isinstance(event.event_id, str)
    assert isinstance(event.timestamp, str)


def test_event_to_dict_from_dict_round_trip():
    original = Event(
        type=EventType.DICE_ROLLED,
        name="attack_roll",
        payload={"roller_id": "plr_01", "dice": "d20", "result": 16},
        source="engine",
    )

    serialized = original.to_dict()
    restored = Event.from_dict(serialized)

    assert restored.event_id == original.event_id
    assert restored.type == EventType.DICE_ROLLED
    assert restored.name == "attack_roll"
    assert restored.payload["result"] == 16
    assert restored.source == "engine"
    assert restored.timestamp == original.timestamp


def test_narration_helper_creates_narration_event():
    event = Event.narration(
        message="You enter the catacombs.",
        source="gm",
        room_id="room_entrance_01",
    )

    assert event.type == EventType.NARRATION
    assert event.name == "narration"
    assert event.source == "gm"
    assert event.payload["message"] == "You enter the catacombs."
    assert event.payload["room_id"] == "room_entrance_01"


def test_state_update_helper_creates_state_update_event():
    event = Event.state_update(
        event_type=EventType.HP_UPDATED,
        name="player_hp_change",
        target_id="plr_inst_01",
        changes={"hp": {"before": 12, "after": 7}},
        source="combat_engine",
        reason="damage_applied",
    )

    assert event.type == EventType.HP_UPDATED
    assert event.name == "player_hp_change"
    assert event.source == "combat_engine"
    assert event.payload["target_id"] == "plr_inst_01"
    assert event.payload["changes"]["hp"]["before"] == 12
    assert event.payload["changes"]["hp"]["after"] == 7
    assert event.payload["reason"] == "damage_applied"

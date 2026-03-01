from core.narration import Narration, create_narration, validate_narration


def test_create_narration_sets_core_fields_and_trims_text():
    narration = create_narration(
        event_id="evt_01",
        text="   The torchlight flickers across the stone walls.   ",
        metadata={"tone": "tense"},
    )

    assert narration.event_id == "evt_01"
    assert narration.text == "The torchlight flickers across the stone walls."
    assert narration.source == "game-master-ai"
    assert narration.metadata["tone"] == "tense"
    assert isinstance(narration.narration_id, str)
    assert isinstance(narration.timestamp, str)


def test_narration_to_dict_from_dict_round_trip():
    original = Narration(
        event_id="evt_02",
        text="The skeleton raises a rusted blade.",
        source="gm",
        metadata={"room_id": "room_crypt_01"},
    )

    serialized = original.to_dict()
    restored = Narration.from_dict(serialized)

    assert restored.narration_id == original.narration_id
    assert restored.event_id == "evt_02"
    assert restored.text == "The skeleton raises a rusted blade."
    assert restored.source == "gm"
    assert restored.metadata["room_id"] == "room_crypt_01"
    assert restored.timestamp == original.timestamp


def test_validate_narration_rejects_missing_event_id_and_text():
    narration = Narration(
        event_id=" ",
        text=" ",
    )

    errors = validate_narration(narration)

    assert "'event_id' is required" in errors
    assert "'text' is required" in errors


def test_from_dict_sets_defaults_when_optional_fields_absent():
    narration = Narration.from_dict(
        {
            "event_id": "evt_03",
            "text": "  The chamber falls silent.  ",
        }
    )

    assert narration.event_id == "evt_03"
    assert narration.text == "The chamber falls silent."
    assert narration.source == "game-master-ai"
    assert narration.metadata == {}
    assert isinstance(narration.narration_id, str)
    assert isinstance(narration.timestamp, str)
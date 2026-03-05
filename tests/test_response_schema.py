import pytest

from agent.response_schema import SchemaValidationError, validate_action_or_clarify, validate_enemy_action


def test_validate_action_or_clarify_accepts_valid_action_payload():
    payload = {
        "type": "query",
        "parameters": {"question": "what can I do?"},
        "metadata": {"source": "test"},
    }
    validate_action_or_clarify(payload)


def test_validate_action_or_clarify_rejects_invalid_payload():
    with pytest.raises(SchemaValidationError):
        validate_action_or_clarify({"foo": "bar"})


def test_validate_enemy_action_rejects_non_combat_action_type():
    with pytest.raises(SchemaValidationError):
        validate_enemy_action(
            {
                "type": "query",
                "actor_instance_id": "enm_01",
                "parameters": {},
            }
        )

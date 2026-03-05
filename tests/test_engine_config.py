from engine.config import load_llm_settings


def test_load_llm_settings_reads_role_temperature_and_max_token_overrides(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "LLM_API_KEY=test_key",
                "LLM_MODEL=gpt-test",
                "LLM_TEMPERATURE=0.3",
                "LLM_TEMPERATURE_ACTION=0.2",
                "LLM_TEMPERATURE_ENEMY=0.25",
                "LLM_TEMPERATURE_NARRATION=0.8",
                "LLM_MAX_TOKENS=4096",
                "LLM_MAX_TOKENS_ACTION=1500",
                "LLM_MAX_TOKENS_NARRATION=3000",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
    monkeypatch.delenv("LLM_TEMPERATURE_ACTION", raising=False)
    monkeypatch.delenv("LLM_TEMPERATURE_ENEMY", raising=False)
    monkeypatch.delenv("LLM_TEMPERATURE_NARRATION", raising=False)
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
    monkeypatch.delenv("LLM_MAX_TOKENS_ACTION", raising=False)
    monkeypatch.delenv("LLM_MAX_TOKENS_NARRATION", raising=False)

    settings = load_llm_settings(dotenv)

    assert settings.api_key == "test_key"
    assert settings.model == "gpt-test"
    assert settings.action_temperature == 0.2
    assert settings.enemy_temperature == 0.25
    assert settings.narration_temperature == 0.8
    assert settings.max_tokens == 4096
    assert settings.action_max_tokens == 1500
    assert settings.narration_max_tokens == 3000

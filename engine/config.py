from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    model: str
    temperature: float
    action_temperature: float
    enemy_temperature: float
    narration_temperature: float
    conversation_temperature: float
    max_tokens: int
    action_max_tokens: int
    enemy_max_tokens: int
    narration_max_tokens: int
    conversation_max_tokens: int
    provider: str = "openai"
    base_url: str = "https://api.openai.com/v1/chat/completions"
    timeout_seconds: float = 30.0


def load_dotenv(dotenv_path: str | Path = ".env") -> Dict[str, str]:
    path = Path(dotenv_path)
    loaded: Dict[str, str] = {}
    if not path.exists():
        return loaded

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded[key] = value

    return loaded


def load_llm_settings(dotenv_path: str | Path = ".env") -> LLMSettings:
    load_dotenv(dotenv_path)

    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower() or "openai"

    try:
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    except ValueError:
        temperature = 0.3

    def _float_env(name: str, fallback: float) -> float:
        try:
            return float(os.getenv(name, str(fallback)))
        except ValueError:
            return fallback

    action_temperature = _float_env("LLM_TEMPERATURE_ACTION", temperature)
    enemy_temperature = _float_env("LLM_TEMPERATURE_ENEMY", temperature)
    narration_temperature = _float_env("LLM_TEMPERATURE_NARRATION", 0.7)
    conversation_temperature = _float_env("LLM_TEMPERATURE_CONVERSATION", 0.6)

    try:
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    except ValueError:
        max_tokens = 4096

    def _int_env(name: str, fallback: int) -> int:
        try:
            parsed = int(os.getenv(name, str(fallback)))
            return parsed if parsed > 0 else fallback
        except ValueError:
            return fallback

    action_max_tokens = _int_env("LLM_MAX_TOKENS_ACTION", max_tokens)
    enemy_max_tokens = _int_env("LLM_MAX_TOKENS_ENEMY", max_tokens)
    narration_max_tokens = _int_env("LLM_MAX_TOKENS_NARRATION", max_tokens)
    conversation_max_tokens = _int_env("LLM_MAX_TOKENS_CONVERSATION", max_tokens)

    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1/chat/completions").strip()

    try:
        timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    except ValueError:
        timeout_seconds = 30.0

    return LLMSettings(
        api_key=api_key,
        model=model,
        temperature=temperature,
        action_temperature=action_temperature,
        enemy_temperature=enemy_temperature,
        narration_temperature=narration_temperature,
        conversation_temperature=conversation_temperature,
        max_tokens=max_tokens,
        action_max_tokens=action_max_tokens,
        enemy_max_tokens=enemy_max_tokens,
        narration_max_tokens=narration_max_tokens,
        conversation_max_tokens=conversation_max_tokens,
        provider=provider,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )

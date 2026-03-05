from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict

from engine.config import LLMSettings
from engine.llm_client import LLMError, LLMRequest


def build_openai_transport(settings: LLMSettings):
    if not settings.api_key:
        raise LLMError("LLM_API_KEY is missing; cannot initialize OpenAI transport")

    endpoint = settings.base_url or "https://api.openai.com/v1/chat/completions"

    def _transport(request: LLMRequest) -> Dict[str, Any]:
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        encoded_body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            endpoint,
            data=encoded_body,
            headers={
                "Authorization": f"Bearer {settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_request, timeout=settings.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else ""
            raise LLMError(f"LLM HTTP error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise TimeoutError(str(exc.reason)) from exc

        choices = raw.get("choices", []) if isinstance(raw.get("choices", []), list) else []
        text = ""
        if choices:
            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            text = str(message.get("content", ""))

        usage_raw = raw.get("usage", {}) if isinstance(raw.get("usage", {}), dict) else {}
        usage = {
            "prompt_tokens": int(usage_raw.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage_raw.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage_raw.get("total_tokens", 0) or 0),
        }

        return {"text": text, "usage": usage, "provider_raw": raw}

    return _transport


def build_transport(settings: LLMSettings):
    if settings.provider == "openai":
        return build_openai_transport(settings)

    raise LLMError(f"Unsupported LLM provider '{settings.provider}'")

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


PROMPT_DIR = Path(__file__).parent / "prompts"


@lru_cache(maxsize=16)
def load_prompt(prompt_name: str) -> str:
    path = PROMPT_DIR / f"{prompt_name}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import load_llm_settings
from engine.state_manager import EngineStateManager


def _check_data_load() -> tuple[bool, str]:
    try:
        session = EngineStateManager("data").create_session()
        if not session.player_templates or not session.dungeon_templates:
            return False, "data templates loaded but catalogs are empty"
        return True, "data templates loaded"
    except Exception as exc:
        return False, f"data load failed: {exc}"


def _check_logs_writable() -> tuple[bool, str]:
    try:
        path = Path("logs/sessions")
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".preflight_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, "logs/sessions writable"
    except Exception as exc:
        return False, f"log path not writable: {exc}"


def _check_env() -> tuple[bool, str]:
    settings = load_llm_settings()
    if settings.api_key:
        return True, "LLM_API_KEY present"
    return False, "LLM_API_KEY missing (live mode will fallback)"


def main() -> None:
    checks = {
        "env": _check_env(),
        "data": _check_data_load(),
        "logs": _check_logs_writable(),
    }

    print("CLI Preflight")
    overall = True
    for name, (ok, message) in checks.items():
        status = "PASS" if ok else "WARN"
        print(f"- {name}: {status} - {message}")
        if name in {"data", "logs"} and not ok:
            overall = False

    if overall:
        print("Preflight result: PASS")
    else:
        print("Preflight result: FAIL")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

# Game Master AI

Deterministic tabletop-style dungeon crawler runtime with optional LLM-assisted parsing, narration, and enemy action selection.

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:
	- `pip install -r requirements.txt`
3. Run tests:
	- `python -m pytest -q`
4. Run the CLI (deterministic local mode):
	- `python main.py`

## Live LLM Mode

1. Copy `.env.example` to `.env`.
2. Set `LLM_API_KEY` and optional model/runtime fields.
3. Run:
	- `python main.py --live-llm`

If live configuration is missing or invalid, runtime falls back to deterministic local agent behavior.

## Current Architecture

- `core/`: canonical deterministic rules, state transitions, validation, and resolution.
- `agent/`: parser/narrator/enemy-ai layer with prompt templates and fallback behavior.
- `engine/`: runtime loop, session lifecycle, LLM client + transport wiring, and logging.

Roadmap and implementation status are maintained in `docs/TODO.md` as the source of truth.
from __future__ import annotations

import argparse

from util.turn_log_replay import replay_turn_log_from_fresh_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay runtime turn logs deterministically")
    parser.add_argument("turn_log", help="Path to *_turns.jsonl runtime log")
    parser.add_argument("--data-dir", default="data", help="Data directory for fresh session templates")
    parser.add_argument(
        "--strict-events",
        action="store_true",
        help="Compare expected and replayed event name lists for each actionable record",
    )
    args = parser.parse_args()

    summary = replay_turn_log_from_fresh_session(
        turn_log_path=args.turn_log,
        data_dir=args.data_dir,
        strict_event_check=args.strict_events,
    )

    print("Replay Summary")
    print(f"- total_records: {summary.total_records}")
    print(f"- actionable_records: {summary.actionable_records}")
    print(f"- replayed_records: {summary.replayed_records}")
    print(f"- skipped_records: {summary.skipped_records}")
    print(f"- mismatched_turns: {summary.mismatched_turns}")
    print(f"- mismatched_event_sets: {summary.mismatched_event_sets}")


if __name__ == "__main__":
    main()

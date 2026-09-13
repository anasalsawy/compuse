"""Command-line application for the compuse coordination core."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from compuse import __version__
from compuse.app.workflow import authorize, run_demo
from compuse.storage import EventIntegrityError, EventStore


def _cmd_version(_: argparse.Namespace) -> int:
    print(f"compuse {__version__}")
    return 0


def _cmd_demo(_: argparse.Namespace) -> int:
    for line in run_demo():
        print(line)
    return 0


def _load_action(raw: str) -> dict:
    if raw.startswith("@"):
        from pathlib import Path

        path = Path(raw[1:])
        if not path.exists():
            raise ValueError(f"action file not found: {path}")
        raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid action JSON: {exc}") from exc


def _cmd_authorize(args: argparse.Namespace) -> int:
    try:
        payload = _load_action(args.action)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        result = authorize(payload, run_id=args.run_id, ttl=args.ttl, journal_path=args.journal)
    except (ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


def _cmd_journal(args: argparse.Namespace) -> int:
    db = EventStore(args.path)
    try:
        if args.verify:
            ok = db.verify(args.run_id)
            print(f"run {args.run_id}: chain verifies={ok}")
            return 0 if ok else 1
        rows = db.events(args.run_id)
        if not rows:
            print(f"run {args.run_id}: no events")
            return 0
        for row in rows:
            print(f"{row['seq']:>4}  {row['type']:<20} {row['timestamp']}  {row['payload']}")
        print(f"--- {len(rows)} event(s), verifies={db.verify(args.run_id)} ---")
        return 0
    except (EventIntegrityError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compuse",
        description="Safety-first coordination core for local-first computer use.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="print the version").set_defaults(func=_cmd_version)

    sub.add_parser("demo", help="run the full lifecycle demonstration").set_defaults(func=_cmd_demo)

    auth = sub.add_parser("authorize", help="propose/issue/consume/release a single action")
    auth.add_argument("action", help="JSON describing the action, e.g. {\"kind\":\"type\",\"text\":\"hi\"}")
    auth.add_argument("--run-id", default="cli-run", help="run identifier (default: cli-run)")
    auth.add_argument("--ttl", type=float, default=30.0, help="permit TTL in seconds (default: 30)")
    auth.add_argument("--journal", default=None, help="SQLite journal path to persist events (default: in-memory)")
    auth.set_defaults(func=_cmd_authorize)

    journal = sub.add_parser("journal", help="inspect or verify a durable event journal")
    journal.add_argument("path", help="path to the SQLite journal file")
    journal.add_argument("--run-id", default="cli-run", help="run identifier (default: cli-run)")
    journal.add_argument("--verify", action="store_true", help="verify the chain instead of listing")
    journal.set_defaults(func=_cmd_journal)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
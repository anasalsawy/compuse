"""CLI entry point for the live NeuralAgent-style Compuse runtime."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from compuse.agent import DualLobeRuntime
from compuse.agent.llm import ModelError, ModelLobeA, ModelLobeB, OpenAICompatibleClient
from compuse.app.desktop import DesktopAdapter, DesktopSafetyError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compuse-agent",
        description="Run a guarded NeuralAgent-style dual-lobe desktop task.",
    )
    parser.add_argument("task", help="natural-language task for the computer-use model")
    parser.add_argument("--live", action="store_true", help="enable physical mouse/keyboard and app input")
    parser.add_argument("--run-id", default="dual-lobe-run", help="durable run identifier")
    parser.add_argument("--journal", default="desktop-web.db", help="SQLite event journal path")
    parser.add_argument("--max-batches", type=int, default=32)
    parser.add_argument("--max-actions-per-batch", type=int, default=8)
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL")
    parser.add_argument("--api-key", default=None, help="API key; prefer COMPUSE_LLM_API_KEY")
    parser.add_argument("--model", default=None, help="vision-capable model name")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--allow-launch",
        action="append",
        default=[],
        metavar="PATH",
        help="allowlist an exact executable path for application.launch (repeatable)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = OpenAICompatibleClient(
            base_url=args.base_url,
            api_key=args.api_key,
            model=args.model,
            timeout=args.timeout,
        )
        adapter = DesktopAdapter(live=args.live, launch_allowlist=args.allow_launch)
        runtime = DualLobeRuntime(
            adapter=adapter,
            lobe_a=ModelLobeA(client),
            lobe_b=ModelLobeB(client),
            run_id=args.run_id,
            journal_path=args.journal,
            max_actions_per_batch=args.max_actions_per_batch,
        )
        report = runtime.run(args.task, max_batches=args.max_batches)
    except (ModelError, DesktopSafetyError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report.model_dump(mode="json", exclude={"final_observation": {"screenshot_data_url"}}), indent=2))
    return 0 if report.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())


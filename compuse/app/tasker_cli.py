"""Interactive Tasker shell for repeated natural-language desktop tasks.

The shell keeps the provider client, desktop adapter, and operator-selected
settings alive for the whole session.  Each submitted task gets its own run
identity and journal chain, while the shell itself remains available when a
task fails, is rejected, or is interrupted.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Sequence

from compuse.agent import (
    DualLobeRuntime,
    LobeBProfile,
    ScreenAwareDualLobeRuntime,
)
from compuse.agent.llm import DynamicModelLobeB, ModelError, ModelLobeA, OpenAICompatibleClient
from compuse.app.desktop import DesktopAdapter, DesktopSafetyError


_COMMANDS = {
    "/help",
    "/status",
    "/config",
    "/architecture",
    "/profile",
    "/trace",
    "/live",
    "/run",
    "/last",
    "/q",
    "/menu",
    "/exit",
    "/quit",
}


@dataclass
class ShellConfig:
    """Settings that remain under the operator's control during a session."""

    architecture: str = "screen-aware"
    lobe_b_profile: LobeBProfile = LobeBProfile.GATEKEEPER
    live: bool = False
    run_id_prefix: str = "tasker-run"
    journal: str = "desktop-web.db"
    max_batches: int = 32
    max_actions_per_batch: int = 8
    screen_poll_interval: float = 0.25
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    timeout: float = 120.0
    trace: bool = False
    allow_launch: tuple[str, ...] = ()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tasker",
        description="Start the interactive NeuralAgent-style Tasker desktop shell.",
    )
    parser.add_argument(
        "initial_task",
        nargs="*",
        help="optional task to run immediately before opening the shell",
    )
    parser.add_argument("--live", action="store_true", help="enable physical mouse/keyboard and app input")
    parser.add_argument("--run-id", default="tasker-run", help="prefix for durable run identifiers")
    parser.add_argument("--journal", default="desktop-web.db", help="SQLite event journal path")
    parser.add_argument("--max-batches", type=int, default=32)
    parser.add_argument("--max-actions-per-batch", type=int, default=8)
    parser.add_argument(
        "--architecture",
        choices=("predictive", "screen-aware"),
        default="screen-aware",
        help="predictive B handoff or continuous screen-aware B watchdog",
    )
    parser.add_argument(
        "--lobe-b-profile",
        choices=tuple(profile.value for profile in LobeBProfile),
        default=LobeBProfile.GATEKEEPER.value,
        help="manually selected B profile; never changed autonomously",
    )
    parser.add_argument("--screen-poll-interval", type=float, default=0.25)
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL")
    parser.add_argument("--api-key", default=None, help="API key; prefer COMPUSE_LLM_API_KEY")
    parser.add_argument("--model", default=None, help="vision-capable model name")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--trace", action="store_true", help="print live A/B/execution overlap events")
    parser.add_argument(
        "--allow-launch",
        action="append",
        default=[],
        metavar="PATH",
        help="allowlist an exact executable path for application.launch (repeatable)",
    )
    parser.add_argument("--no-banner", action="store_true", help="suppress the startup banner")
    return parser


class TaskerShell:
    """Long-lived command shell around the real model-backed runtime."""

    def __init__(
        self,
        config: ShellConfig,
        *,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> None:
        self.config = config
        self.input_fn = input_fn
        self.output_fn = output_fn
        self.client = OpenAICompatibleClient(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model,
            timeout=config.timeout,
        )
        self.adapter = DesktopAdapter(
            live=config.live,
            launch_allowlist=config.allow_launch,
        )
        self.lobe_a = ModelLobeA(self.client)
        self.lobe_b = DynamicModelLobeB(self.client, profile=config.lobe_b_profile)
        self.run_number = 0
        self.last_report: object | None = None

    def write(self, message: str = "") -> None:
        self.output_fn(message)

    def trace(self, line: str) -> None:
        if self.config.trace:
            self.write(line)

    def banner(self) -> None:
        self.write("Tasker interactive shell")
        self.write("Type a natural-language task, /help for commands, or /exit to quit.")
        self.write(
            f"architecture={self.config.architecture} "
            f"lobe_b_profile={self.config.lobe_b_profile.value} "
            f"live={str(self.config.live).lower()}"
        )
        self.write()

    def prompt(self) -> str:
        return f"tasker[{self.config.architecture}/{self.config.lobe_b_profile.value}]> "

    def _new_run_id(self) -> str:
        self.run_number += 1
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{self.config.run_id_prefix}-{stamp}-{self.run_number}"

    def _runtime(self, run_id: str):
        if self.config.architecture == "predictive":
            return DualLobeRuntime(
                adapter=self.adapter,
                lobe_a=self.lobe_a,
                lobe_b=self.lobe_b,
                run_id=run_id,
                journal_path=self.config.journal,
                max_actions_per_batch=self.config.max_actions_per_batch,
                trace=self.trace if self.config.trace else None,
            )
        return ScreenAwareDualLobeRuntime(
            adapter=self.adapter,
            lobe_a=self.lobe_a,
            screen_lobe=self.lobe_b,
            run_id=run_id,
            journal_path=self.config.journal,
            max_actions_per_batch=self.config.max_actions_per_batch,
            screen_poll_interval=self.config.screen_poll_interval,
            trace=self.trace if self.config.trace else None,
        )

    def run_task(self, task: str) -> None:
        task = task.strip()
        if not task:
            return
        run_id = self._new_run_id()
        self.write(f"[Tasker] starting run_id={run_id}")
        runtime = None
        try:
            runtime = self._runtime(run_id)
            report = runtime.run(task, max_batches=self.config.max_batches)
            self.last_report = report
            self.write(
                f"[Tasker] status={report.status} "
                f"batches={report.batches_executed} "
                f"discarded={report.batches_discarded} "
                f"actions={report.actions_executed}"
            )
            self.write(json.dumps(report.model_dump(mode="json", exclude={"final_observation": {"screenshot_data_url"}}), indent=2))
        except KeyboardInterrupt:
            self.write("[Tasker] task interrupted; the shell is still running.")
        except (ModelError, DesktopSafetyError, ValueError, RuntimeError) as exc:
            self.write(f"[Tasker] task failed safely: {exc}")
        except Exception as exc:  # noqa: BLE001 - a task error must not terminate the shell
            self.write(f"[Tasker] unexpected task error ({type(exc).__name__}): {exc}")
        finally:
            if runtime is not None:
                runtime.store.close()

    def show_config(self) -> None:
        key_state = "set" if self.client.api_key else "missing"
        self.write(json.dumps({
            "architecture": self.config.architecture,
            "lobe_b_profile": self.config.lobe_b_profile.value,
            "live": self.config.live,
            "journal": self.config.journal,
            "run_id_prefix": self.config.run_id_prefix,
            "max_batches": self.config.max_batches,
            "max_actions_per_batch": self.config.max_actions_per_batch,
            "screen_poll_interval": self.config.screen_poll_interval,
            "base_url": self.client.base_url,
            "model": self.client.model,
            "api_key": key_state,
            "timeout": self.client.timeout,
            "trace": self.config.trace,
            "allow_launch": list(self.config.allow_launch),
        }, indent=2))

    def show_status(self) -> None:
        self.write(
            f"architecture={self.config.architecture}, "
            f"lobe_b_profile={self.config.lobe_b_profile.value}, "
            f"live={str(self.config.live).lower()}, "
            f"trace={str(self.config.trace).lower()}, "
            f"runs={self.run_number}, "
            f"journal={self.config.journal}"
        )
        if self.last_report is not None:
            self.write(
                f"last_status={self.last_report.status} "
                f"last_run_id={self.last_report.run_id}"
            )

    def show_help(self) -> None:
        self.write("Enter any natural-language task to run it.")
        self.write("/status       show current settings and last run")
        self.write("/config       show complete configuration (API key is redacted)")
        self.write("/architecture predictive|screen-aware")
        self.write("/profile base|predictive|screen-aware|gatekeeper|recovery")
        self.write("/trace on|off  toggle live runtime events")
        self.write("/live on|off  toggle physical desktop input")
        self.write("/run TASK     explicit task form; plain text works too")
        self.write("/last         print the last report again")
        self.write("/exit         close the shell")

    def _prompt_session(self):
        """Build the Codex-style slash completion prompt when available."""
        if self.input_fn is not input or not sys.stdin.isatty():
            return None
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.completion import WordCompleter
        except ImportError:
            return None
        descriptions = {
            "/help": "show commands",
            "/status": "show current session status",
            "/config": "show configuration; key redacted",
            "/architecture": "switch predictive or screen-aware",
            "/profile": "switch the manually selected B profile",
            "/trace": "toggle runtime trace output",
            "/live": "toggle physical desktop input",
            "/run": "run an explicit task",
            "/last": "show the last report",
            "/menu": "show the slash-command menu",
            "/exit": "close Tasker",
            "/quit": "close Tasker",
        }
        completer = WordCompleter(
            list(descriptions),
            meta=descriptions,
            sentence=False,
            match_middle=False,
        )
        return PromptSession(completer=completer)

    def _set_architecture(self, value: str) -> None:
        if value not in {"predictive", "screen-aware"}:
            self.write("usage: /architecture predictive|screen-aware")
            return
        self.config.architecture = value
        self.write(f"architecture set to {value} for future tasks")

    def _set_profile(self, value: str) -> None:
        try:
            profile = LobeBProfile(value)
        except ValueError:
            self.write("usage: /profile base|predictive|screen-aware|gatekeeper|recovery")
            return
        self.config.lobe_b_profile = profile
        self.lobe_b = DynamicModelLobeB(self.client, profile=profile)
        self.write(f"Lobe B profile set to {profile.value} for future tasks")

    def _set_live(self, value: str) -> None:
        normalized = value.strip().lower()
        if normalized in {"on", "true", "1"}:
            self.config.live = True
            self.adapter.live = True
            self.write("live desktop input enabled for future tasks")
        elif normalized in {"off", "false", "0"}:
            self.config.live = False
            self.adapter.live = False
            self.write("live desktop input disabled for future tasks")
        else:
            self.write("usage: /live on|off")

    def handle_line(self, line: str) -> bool:
        """Handle one line. Return False when the shell should exit."""
        stripped = line.strip()
        if not stripped:
            return True
        lowered = stripped.lower()
        if lowered in {"exit", "quit", "/exit", "/quit", "/q"}:
            return False
        if lowered in {"/", "/?", "menu", "/menu"}:
            self.show_help()
            return True
        if lowered in {"help", "/help"}:
            self.show_help()
            return True
        if lowered in {"status", "/status"}:
            self.show_status()
            return True
        if lowered in {"config", "/config"}:
            self.show_config()
            return True
        if lowered in {"last", "/last"}:
            if self.last_report is None:
                self.write("no task has completed in this session")
            else:
                self.write(json.dumps(self.last_report.model_dump(mode="json", exclude={"final_observation": {"screenshot_data_url"}}), indent=2))
            return True
        if stripped.startswith("/architecture"):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 1:
                self.write(f"architecture={self.config.architecture}")
            else:
                self._set_architecture(parts[1].strip())
            return True
        if stripped.startswith("/profile"):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 1:
                self.write(f"lobe_b_profile={self.config.lobe_b_profile.value}")
            else:
                self._set_profile(parts[1].strip())
            return True
        if stripped.startswith("/trace"):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 1:
                self.write(f"trace={str(self.config.trace).lower()}")
            elif parts[1].strip().lower() in {"on", "true", "1"}:
                self.config.trace = True
                self.write("trace enabled for future tasks")
            elif parts[1].strip().lower() in {"off", "false", "0"}:
                self.config.trace = False
                self.write("trace disabled for future tasks")
            else:
                self.write("usage: /trace on|off")
            return True
        if stripped.startswith("/live"):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 1:
                self.write(f"live={str(self.config.live).lower()}")
            else:
                self._set_live(parts[1])
            return True
        if stripped.startswith("/run"):
            task = stripped[4:].strip()
            if not task:
                self.write("usage: /run TASK")
            else:
                self.run_task(task)
            return True
        if stripped.startswith("/"):
            command = stripped.split(maxsplit=1)[0].lower()
            if command not in _COMMANDS:
                self.write(f"unknown command: {command}; use /help")
            return True
        self.run_task(stripped)
        return True

    def run(self, *, initial_tasks: Sequence[str] = ()) -> int:
        for task in initial_tasks:
            self.run_task(task)
        prompt_session = self._prompt_session()
        while True:
            try:
                if prompt_session is None:
                    line = self.input_fn(self.prompt())
                else:
                    line = prompt_session.prompt(
                        self.prompt(),
                        complete_while_typing=True,
                    )
            except EOFError:
                self.write()
                self.write("[Tasker] session closed.")
                return 0
            except KeyboardInterrupt:
                self.write()
                self.write("[Tasker] use /exit to close the session.")
                continue
            if not self.handle_line(line):
                self.write("[Tasker] session closed.")
                return 0


def _config_from_args(args: argparse.Namespace) -> ShellConfig:
    if args.max_batches < 1:
        raise ValueError("--max-batches must be positive")
    if not 1 <= args.max_actions_per_batch <= 8:
        raise ValueError("--max-actions-per-batch must be between 1 and 8")
    if args.screen_poll_interval <= 0:
        raise ValueError("--screen-poll-interval must be positive")
    if args.timeout <= 0:
        raise ValueError("--timeout must be positive")
    return ShellConfig(
        architecture=args.architecture,
        lobe_b_profile=LobeBProfile(args.lobe_b_profile),
        live=args.live,
        run_id_prefix=args.run_id,
        journal=args.journal,
        max_batches=args.max_batches,
        max_actions_per_batch=args.max_actions_per_batch,
        screen_poll_interval=args.screen_poll_interval,
        base_url=args.base_url,
        api_key=args.api_key,
        model=args.model,
        timeout=args.timeout,
        trace=args.trace,
        allow_launch=tuple(args.allow_launch),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        config = _config_from_args(args)
        shell = TaskerShell(config)
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
        return 2
    if not args.no_banner:
        shell.banner()
    return shell.run(initial_tasks=(" ".join(args.initial_task),) if args.initial_task else ())


if __name__ == "__main__":
    raise SystemExit(main())

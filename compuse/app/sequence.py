"""Multi-step browser run: every step gets its own permit in the journal."""
from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from compuse.protocol import Action, WebOp
from compuse.coordinator import Coordinator
from compuse.storage import EventStore
from compuse.app.browser import BrowserEngine, BrowserError
from compuse.app.workflow import run_coordinated_step

Strict: TypeAdapter = TypeAdapter(list[WebOp])


def load_steps(path: str) -> list[WebOp]:
    import json

    if path == "-":
        import sys

        raw = json.load(sys.stdin)
    elif not path.startswith("@"):
        with open(path, "r", encoding="utf-8-sig") as fh:
            raw = json.load(fh)
    else:
        from compuse.app.cli import _load_action

        raw = _load_action(path)
    return Strict.validate_python(raw)


def run_steps(steps: list[WebOp], *, run_id: str = "cli-run", ttl: float = 30.0,
              journal_path: str | None = None,
              browser: BrowserEngine | None = None) -> dict[str, Any]:
    """Execute ``steps`` in order; each step is proposed/consumed/executed/released."""
    store = EventStore(journal_path if journal_path else ":memory:")
    coordinator = Coordinator(store=store)
    lines: list[str] = []
    results: list[dict[str, Any]] = []
    failures = 0
    engine = browser if browser is not None else BrowserEngine()

    def runner(action: Action) -> dict[str, Any]:
        return engine.run_webop(action)

    try:
        if browser is None:
            engine.start()
        for revision, action in enumerate(steps):
            try:
                step = run_coordinated_step(coordinator, action, run_id=run_id, revision=revision,
                                            ttl=ttl, executor_fn=runner)
                execution = step["execution"]
                ok = bool(execution.get("performed"))
                lines.append(f"{step['step']:>4} {str(action.op):<6} {execution.get('detail', '')}"
                             + ("" if ok else "   [not performed]"))
                if not ok:
                    failures += 1
                results.append(step)
            except (BrowserError, ValueError, RuntimeError) as exc:
                failures += 1
                lines.append(f"{revision + 1:>4} ERROR  {exc}")
                results.append({"step": revision + 1, "execution": {"performed": False,
                                                                     "detail": str(exc)}})
    finally:
        engine.close()

    return {
        "run_id": run_id,
        "steps": len(steps),
        "failures": failures,
        "transcript": lines,
        "results": results,
        "journal_events": len(store.events(run_id)),
        "journal_verifies": store.verify(run_id),
    }


__all__ = ["load_steps", "run_steps"]
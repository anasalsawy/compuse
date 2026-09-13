# Compuse

Compuse is a local-first desktop computer-use runtime with an explicit
authorization and audit boundary. It now includes a first NeuralAgent-style
Windows vertical slice: headed screen observation, typed physical input, an
OpenAI-compatible vision planner, and a dual-lobe speculative handoff loop.

## Dual-lobe runtime

Lobe A plans the active batch. While that batch is executing, A predicts a
possible next batch and Lobe B independently prepares and checks the next
handoff from A's predicted end state. B's batch is executed only after a fresh
observation confirms its checkable anchors. Any mismatch, failure, or unknown
result discards speculation and causes a replan from reality.

This overlaps model planning with physical execution, but physical input stays
serialized through the Coordinator. It is bounded speculation, not blind
parallel clicking.

## Install and run on Windows

```powershell
python -m pip install -e ".[desktop]"
$env:COMPUSE_LLM_BASE_URL = "https://api.example.com/v1"
$env:COMPUSE_LLM_API_KEY = "your-key"
$env:COMPUSE_LLM_MODEL = "your-vision-model"
compuse-agent "Open Chrome and navigate to example.com" --live
```

Use `--live` only after reviewing the task. Without it, the desktop adapter
refuses mouse, keyboard, launch, file, and browser mutations.

## Prove the loop from a shell

Run the deterministic comparison first. It uses the real runtime classes on
the same multi-stage task, prints timestamps, and performs no desktop input:

```powershell
compuse-dual-loop-demo --scenario complex --architecture compare
```

The output compares three designs:

- `control`: one loop plans the next batch only after the current batch
  finishes and is observed. This is the baseline planning-gap control group.
- `predictive`: A predicts the next batch while the current batch executes and
  B independently prepares the handoff from A's predicted end.
- `screen-aware`: A predicts the next batch while B continuously samples and
  assesses the screen, interrupts unsafe execution at an action boundary, and
  gates the handoff against the fresh screen.

Run one proof alone with `--architecture control`, `--architecture predictive`,
or `--architecture screen-aware`. The control proof ends in
`CONTROL_BASELINE=PASS`; each dual-lobe proof ends in
`CONTINUOUS_HANDOFF=PASS`; the three-way comparison ends in `COMPARISON=PASS`.

To see either architecture use the real model and desktop adapter, add
`--trace` and select the architecture explicitly:

```powershell
compuse-agent "Open Chrome and navigate to example.com" --architecture predictive --live --trace
compuse-agent "Open Chrome and navigate to example.com" --architecture screen-aware --live --trace
```

The screen-aware mode intentionally limits B to one in-flight vision
assessment while capture continues. Sending every captured frame to a model
would create a queue and increase latency instead of improving awareness.

## Portable core

The original coordination core remains available and provides:

- strict Pydantic v2 action models;
- observation/action binding;
- one-use expiring permits;
- SQLite WAL event journaling with a SHA-256 hash chain;
- fail-closed lifecycle transition tables.

```powershell
python -m pip install -e ".[test]"
python -m pytest -ra
```

The portable tests do not prove Windows behavior. The live adapter is a first
vertical slice and still needs UI Automation/OCR grounding, independent
postcondition verification, durable permit state, cancellation, crash
recovery, and interactive Windows acceptance tests before unattended use.

See [`docs/dual-lobe.md`](docs/dual-lobe.md) for the runtime contract and
[`docs/windows-development.md`](docs/windows-development.md) for the Windows
boundary.

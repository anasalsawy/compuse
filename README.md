# Tasker

Tasker is a local-first desktop computer-use runtime with an explicit
authorization and audit boundary. It now includes a first NeuralAgent-style
Windows vertical slice: headed screen observation, typed physical input, an
OpenAI-compatible vision planner, and a dual-lobe speculative handoff loop.

## Start the interactive app

Tasker is a persistent command shell, not only a one-shot command. Start it
once, then enter natural-language tasks at the `tasker>` prompt:

```powershell
tasker
```

Inside the shell:

```text
tasker[screen-aware/gatekeeper]> Open Chrome and navigate to https://example.com
tasker[screen-aware/gatekeeper]> Find the page title
tasker[screen-aware/gatekeeper]> /profile recovery
tasker[screen-aware/recovery]> /architecture predictive
tasker[predictive/recovery]> /status
tasker[predictive/recovery]> /exit
```

In a normal terminal, typing `/` opens the slash-command completion menu while
you type. Press Tab or Enter to select a command. Typing `/` and pressing
Enter also prints the command menu as a fallback.

The model client and desktop adapter remain loaded across tasks. Each task
gets a separate run ID and its own hash-chained journal entries in the same
SQLite journal. A failed task is reported and the shell stays open. The
operator can manually change the architecture, B profile, and trace setting;
the profile never changes autonomously. Use `/help` to see every shell
command. API keys are never printed by `/config`.

The user-facing command is `tasker`. `tasker-agent` remains available for
scripts that intentionally run exactly one task and then exit, while
`tasker-demo` runs the deterministic shell proof.

## Dual-lobe runtime

Lobe A plans the active batch. While that batch is executing, A predicts a
possible next batch and Lobe B independently prepares and checks the next
handoff from A's predicted end state. B's batch is executed only after a fresh
observation confirms its checkable anchors. Any mismatch, failure, or unknown
result discards speculation and causes a replan from reality.

This overlaps model planning with physical execution, but physical input stays
serialized through the Coordinator. It is bounded speculation, not blind
parallel clicking.

### Always-on B core and manual profiles

Every model-backed B decision includes the same core review. B broadens the
working context with useful notes, missing prerequisites, failure modes, and
unasked questions. It also reviews claims for deception and records proof
requirements. `GREEN` means “no deception detected”; it does not mean that a
claim is guaranteed true. Claims about creating or changing an artifact require
the full artifact as proof, not only a manifest or summary.

The operator selects B's additional profile before each run. The profile stays
fixed and never changes autonomously:

| Profile | Additional emphasis |
| --- | --- |
| `base` | Always-on context broadening and anti-deception review |
| `predictive` | Prepare the next bounded batch from A's predicted endpoint |
| `screen-aware` | Ground decisions in visible screen transitions |
| `gatekeeper` | Reject decisions with missing proof or a non-GREEN grade |
| `recovery` | Diagnose failures and require safe recovery prerequisites |

`--architecture` selects the execution loop (`predictive` or `screen-aware`).
`--lobe-b-profile` selects B's manually chosen emphasis. The profile is an
additional policy layer; it does not replace the always-on core. Core review
events appear in `--trace` output as `B state=CORE_REVIEW`, and prior B notes
are injected internally into later planning without changing the user's task.

## Install and run on Windows

```powershell
cd C:\Projects
git clone --branch main --single-branch `
  https://github.com/anasalsawy/compuse.git tasker
cd tasker
python -m pip --isolated install --user -e ".[desktop,test]"
$env:COMPUSE_LLM_BASE_URL = "https://api.example.com/v1"
$env:COMPUSE_LLM_API_KEY = "your-key"
$env:COMPUSE_LLM_MODEL = "your-vision-model"
tasker
tasker-agent "Open Chrome and navigate to example.com" `
  --architecture predictive --lobe-b-profile base --live --trace
```

Replace the example URL, API URL, key, and model with your real values. The
`desktop` extra installs Windows input dependencies; the `test` extra installs
the test runner.

Use `--live` only after reviewing the task. Without it, the desktop adapter
refuses mouse, keyboard, launch, file, and browser mutations.

## Prove the loop from a shell

Run the deterministic comparison first. It uses the real runtime classes on
the same multi-stage task, prints timestamps, and performs no desktop input:

```powershell
tasker-demo --scenario complex --architecture compare `
  --lobe-b-profile gatekeeper
```

The output compares three designs:

- `control`: one loop plans the next batch only after the current batch
  finishes and is observed. This is the baseline planning-gap control group.
- `predictive`: A predicts the next batch while the current batch executes and
  B independently prepares the handoff from A's predicted end.
- `screen-aware`: A predicts the next batch while B continuously samples and
  assesses the screen, interrupts unsafe execution at an action boundary, and
  gates the handoff against the fresh screen.

Run one deterministic proof alone with `--architecture control`,
`--architecture predictive`, or `--architecture screen-aware`. The control proof ends in
`CONTROL_BASELINE=PASS`; each dual-lobe proof ends in
`CONTINUOUS_HANDOFF=PASS`; the three-way comparison ends in `COMPARISON=PASS`.

### Parallel split prototype

The prototype also tests a different dual-loop architecture. A front-door
split planner looks for one safe breaking point. If it finds independent
surfaces and non-overlapping resources, Loop A and Loop B execute their own
bounded branch plans concurrently. A verified join gate then runs one merge
batch after both final observations match their predicted end anchors.

This is not blind parallel clicking: the runtime refuses a split when both
lanes use the same coordinate space or declare the same exclusive resource.
The lanes must be isolated windows, workspaces, browser profiles, or machines;
one ordinary desktop cannot safely accept two simultaneous physical input
streams. The shell proof is deterministic and does not touch the real desktop.

Run the split prototype and its same-work control group:

```powershell
tasker-demo --architecture parallel --lobe-b-profile gatekeeper
tasker-demo --architecture parallel-control --lobe-b-profile gatekeeper
```

Use `--architecture compare` to include both split designs alongside the
original control, predictive, and screen-aware comparisons. A successful
parallel proof ends in `PARALLEL_SPLIT=PASS`, while the serial split baseline
ends in `SPLIT_CONTROL_BASELINE=PASS`. The model-backed `ModelSplitPlanner`
uses the same strict `ParallelSplitPlan` contract; live two-surface adapters
are still required before enabling physical parallel input.

For the live agent, use `--architecture predictive` or
`--architecture screen-aware`, add `--trace`, and select the B profile
explicitly:

```powershell
tasker-agent "Open Chrome and navigate to example.com" `
  --architecture predictive --lobe-b-profile base --live --trace
tasker-agent "Open Chrome and navigate to example.com" `
  --architecture screen-aware --lobe-b-profile screen-aware --live --trace
```

The screen-aware mode intentionally limits B to one in-flight vision
assessment while capture continues. Sending every captured frame to a model
would create a queue and increase latency instead of improving awareness.

For the screen-aware loop, choose the screen-aware architecture and select the
profile manually:

```powershell
tasker-agent "Open Chrome and navigate to example.com" `
  --architecture screen-aware --lobe-b-profile screen-aware --live --trace
```

Use `--lobe-b-profile gatekeeper` when unsupported claims must block the next
handoff. The screen watcher itself remains continuous, but the full core
review runs at B's decision boundaries rather than sending every captured frame
through the larger reasoning prompt.

## Portable core

The original coordination core remains available and provides:

- strict Pydantic v2 action models;
- observation/action binding;
- one-use expiring permits;
- SQLite WAL event journaling with a SHA-256 hash chain;
- fail-closed lifecycle transition tables.

```powershell
python -m pip --isolated install --user -e ".[test]"
python -m pytest -ra
```

The portable tests do not prove Windows behavior. The live adapter is a first
vertical slice and still needs UI Automation/OCR grounding, independent
postcondition verification, durable permit state, cancellation, crash
recovery, and interactive Windows acceptance tests before unattended use.

See [`docs/dual-lobe.md`](docs/dual-lobe.md) for the runtime contract and
[`docs/windows-development.md`](docs/windows-development.md) for the Windows
boundary.

# Windows development

The `tasker-agent` vertical slice uses a headed desktop adapter. Install the
optional dependencies on Windows with:

```powershell
python -m pip install -e ".[desktop]"
```

The adapter captures a PNG screenshot, active-window/process/session metadata,
and optional UI Automation labels. With `--live`, it can execute the typed
mouse, keyboard, launch, file, and browser actions through the Coordinator.
Without `--live`, physical input is refused.

Before native behavior can be treated as production-ready, tests must run on
an unlocked interactive Windows desktop and report the Windows build, Python
version, helper version, session, input desktop, foreground window, process
identity, display topology, and DPI. CI on non-Windows hosts is not evidence
of desktop safety.

The current slice still needs independent postcondition verification, durable
permit state, cancellation/emergency stop, crash recovery, stronger UIA
grounding, and an installer/signing workflow. Do not use it for unattended
desktop mutation or production credentials until those controls are complete.

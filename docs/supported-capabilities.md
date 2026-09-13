# Supported capabilities

| Capability | Status |
|---|---|
| Strict typed protocol models | Implemented |
| Observation/action binding | Implemented |
| One-use expiring in-process permits | Implemented |
| SQLite tamper-evident event journal | Implemented |
| Fail-closed lifecycle transition tables | Implemented |
| Speculative typed action batches | Implemented |
| Concurrent A/B planning during execution | Implemented |
| Predicted-end precondition gate | Implemented |
| OpenAI-compatible vision model adapter | Implemented |
| Headed desktop screenshots | Windows vertical slice; optional dependency |
| Real mouse/keyboard input | Windows vertical slice; requires `--live` |
| Win32 foreground-window/process identity | Windows vertical slice |
| UI Automation visible markers | Optional when `pywinauto` is installed |
| Independent postcondition verifier | Not implemented |
| Durable permits, leases, and restart recovery | Not implemented |
| Cancellation and emergency stop | Not implemented |
| Installer and code signing | Not implemented |
| Unattended production operation | Not supported |

Implemented runtime capabilities are covered by portable tests where possible;
the Windows rows still require interactive Windows acceptance tests.

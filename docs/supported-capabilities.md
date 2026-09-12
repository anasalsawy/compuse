# Supported capabilities

Status values are deliberately conservative: `supported` means implemented and tested in this portable core; `planned` means specified but absent; `requires user intervention` means the agent must pause.

| Capability | Status | Boundary |
|---|---|---|
| Strict typed protocol | supported | Pydantic models; limited action set |
| Observation-bound permits | supported | In-process permit registry; restart durability is not implemented |
| Exact action/policy/coordinate binding | supported | Coordinator checks on issue and consume |
| Thread-safe mutation boundary | supported | One Coordinator process only |
| SQLite hash-chain journal | supported | WAL/FULL configuration; no external tamper prevention |
| Windows UIA and input | planned | Not implemented |
| DPI/transforms/session safety | planned | Not implemented |
| Browser/Playwright/CDP isolation | planned | Not implemented |
| Electron renderer/main/IPC | planned | Not implemented |
| Voice, confirmation tokens, emergency stop | planned | Not implemented |
| Independent verification/recovery/watchdog | planned | Not implemented |
| Credentials, MFA, UAC, secure desktop | requires user intervention | Never autonomous in MVP |
| Arbitrary shell/code execution | unsupported | Not part of the product contract |

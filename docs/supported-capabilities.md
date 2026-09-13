# Supported capabilities

Statuses are conservative: **supported** means implemented and covered by the portable Python tests; **planned** means specified but absent; **deferred** means intentionally outside the first milestone; **unsupported** means outside the product contract.

| Capability | Status | Boundary |
|---|---|---|
| Strict typed protocol | supported | `compuse/protocol/models.py`; Pydantic models and discriminated actions |
| Observation-bound permits | supported | In-process permit registry; restart durability is not implemented |
| Exact action/policy/coordinate binding | supported | Coordinator validates issue and consume paths |
| Single-use and expiry | supported | In-process mutation boundary; durable permits are planned |
| SQLite hash-chain journal | supported | `compuse/storage/events.py`; tamper evidence, not tamper prevention |
| Durable run/action state | planned | Requires schema, repositories, migrations, and recovery |
| Durable leases and idempotency | planned | Not implemented |
| Windows UI Automation | planned | No native helper exists |
| Notepad semantic text workflow | planned | First Windows milestone; not implemented |
| Process/window/session safety | planned | No Windows implementation exists |
| Independent verification and recovery | planned | No executor/native boundary exists |
| Browser/Playwright/CDP | deferred | Not part of the first milestone |
| Voice | deferred | Must use the same Coordinator authority |
| Provider/model integration | deferred | Provider output cannot authorize actions |
| Electron | deferred | No renderer exists |
| Screenshots or physical input | deferred | No capture or `SendInput` implementation exists |
| Arbitrary shell/code execution | unsupported | Outside the product contract |
| Course scheduling/calendar | unsupported | Not the repository domain |

Portable tests do not validate Windows behavior. Windows claims require an interactive Windows environment and native integration tests.
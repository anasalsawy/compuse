# Security boundary

Compuse is a coordination prototype, not an unrestricted automation shell.

- Provider, environment, and voice content are untrusted data.
- Only the Coordinator may issue or consume permits.
- Arbitrary executable paths, shell commands, credentials, MFA, secure-desktop automation, and normal browser-profile attachment are outside the contract.
- Consuming a permit is not execution success. Future executors must report dispatch certainty and independent verification separately.
- Unknown outcomes must enter reconciliation; they must never be blindly retried.
- Event hash chains provide tamper evidence. They do not provide encryption, access control, or tamper prevention.
- Do not log secrets, clipboard contents, passwords, tokens, or full text by default.
- The current implementation keeps permit authority in process memory; it is not restart-safe.

Before a Windows release, define artifact retention, database backup/migration, secret storage, native-helper versioning, cancellation, emergency stop, code signing, and an interactive test matrix.
# ADR 0004: Hash-chained receipts instead of plain logs

## Status

Accepted.

## Context

An ordinary log can be edited, reordered or truncated without a trace, so it cannot settle a dispute about what an agent did. `agent-trace-receipts` writes each step into a chain keyed by a secret you hold, and its verifier refuses a bad chain. `llm-data-boundary` writes a hash-chained evidence record for each decision, and its verifier refuses a record that was edited, reordered or forged. `llmops-release-monitor` keeps a tamper-evident audit log for release decisions.

## Decision

Every record that may later serve as evidence is a receipt: it is chained to the one before it and checked by a verifier that fails on any break. Verification is a required step in the release path, not an optional audit. A missing or short signing key stops tracing instead of falling back to an unsigned log.

## Alternatives considered

- Plain application logs: simple, searchable, not evidence.
- A log shipped to a write-once store: strong, but depends on infrastructure the other repositories do not assume.
- A signature on each record without chaining: detects edits, not deletion or reordering.

## Consequences

- Tampering, reordering and gaps become verifier failures with a named reason.
- The key becomes a real dependency: its custody, rotation and loss need an owner.
- Receipts are not a substitute for logs used for debugging. Both exist, and only receipts are cited as evidence.

## Trade-offs

Chained receipts cost key management and a strict write path. When the key is unavailable, the design stops writing evidence rather than writing weaker evidence, which is the fail-closed choice from ADR 0002 applied to the audit trail.

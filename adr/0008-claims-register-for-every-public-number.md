# ADR 0008: A claims register for every public number

## Status

Accepted.

## Context

A number in a README that no command produces is a claim nobody can check, and it goes stale when the code changes. Other repositories in this design guard against this in their own way: one fails a test if its results table drifts from the code, another records a hash of its sample cases and fails if a case or label changes without a new hash, and `blind-eval-harness` states plainly that a pre-registered hash it cannot publish proves nothing a reader can check.

## Decision

Every number in public material is produced by a command, and a register row lists the number, the command that prints it and the file it appears in. A project that quotes figures keeps those rows and a check that fails the build when a published number no longer matches its command. This repository takes the simplest form of the rule: prose carries no figures of its own, and numbers appear only as the output of `scripts/verify.sh` and the cost model, so there are no rows to keep. A claim a reader cannot reproduce is either removed or labeled as unverifiable.

## Alternatives considered

- Numbers typed by hand into prose: fast, and the first to drift.
- A dashboard of live numbers: current, but not a stable thing to cite or hash.
- No numbers at all: safe, but gives a reader nothing to verify.

## Consequences

- Updating a result is a two-step change: the code and its register row move together.
- Illustrative inputs, such as the example prices in `capacity/example.yaml`, are labeled as illustrative and never presented as measured.
- A reviewer can reproduce any figure from a clean checkout with one command.

## Trade-offs

A register is bookkeeping that slows small edits. We accept the slowdown because the alternative is a public number that cannot be defended when someone checks it.

# ADR 0007: Replayed cassettes instead of live calls in CI

## Status

Accepted.

## Context

A CI job that calls a live model is slow, costs money, needs a secret, and can fail or change for reasons unrelated to the commit. `prompt-regression-suite` keeps fixtures with a recorded response per prompt version, lints the templates, and fails the build when a new version regresses a case an older version passed. It uses no network and no model call. `llmops-release-monitor` proves its checks by planting a failure and requiring the check to catch it.

## Decision

CI replays recorded responses (cassettes) and never calls a live model. A cassette is committed, versioned with the prompt it belongs to, and replaced only by an explicit refresh step that is reviewed like code. Live behavior is measured after release by the monitor on canary traffic, not in the build.

## Alternatives considered

- Live calls on every commit: closest to production, but flaky, slow, costly and unreproducible.
- Live calls on a schedule only: catches drift, but misses a regression until the schedule runs.
- No recorded responses, rules only: cannot detect a change in output shape or refusal behavior.

## Consequences

- The build is deterministic, offline and free to rerun.
- A stale cassette can pass a prompt that a live model would now fail, so cassette age is tracked and refreshed on a schedule.
- Drift and live quality are the monitor's job on the release path, not the build's.

## Trade-offs

We give up fidelity to live behavior in exchange for a build that is reproducible and cheap. The gap is covered by canary rollback after release, which is why replay and monitoring are paired rather than chosen between.

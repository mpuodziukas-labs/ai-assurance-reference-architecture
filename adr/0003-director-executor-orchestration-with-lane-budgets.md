# ADR 0003: Director and executor orchestration with per-lane token budgets

## Status

Accepted.

## Context

When several agents work on one repository, three failures repeat: two agents edit the same file, one agent spends far more than planned, and an agent reports success that the code does not support. The `orchestrator/` directory in this repository is a small runnable model of the countermeasure, built on mock agents with no network and no model calls.

## Decision

A director splits work into lanes. Each lane owns a disjoint set of files and has a token budget, and the plan is rejected before any work starts if lanes overlap or budgets exceed the total. Executors run against a copy of the workspace. A verifier, not the executor, then diffs the workspace, compares the claimed usage to the lane budget, and re-runs the lane's check. A lane that exceeds its budget, touches a file it does not own, deletes a foreign file, raises an error or fails the re-run is rejected and none of its changes are merged.

## Alternatives considered

- One agent for everything: no overlap, but no parallelism and one context holds the whole task.
- Agents share a workspace and resolve conflicts afterward: merges hide who broke what.
- Trust the executor's own report: cheapest, and exactly the failure this ADR exists to stop.

## Consequences

- Every rejection carries a reason code (budget, scope, check, agent error, missing agent) that a human can act on.
- A rejected lane costs its tokens but changes nothing.
- Lane boundaries must be decided up front, which forces the file ownership question early.

## Trade-offs

Disjoint lanes and re-verification add planning effort and some duplicated checking. We accept that because the alternative is discovering overlap at merge time. The orchestrator here proves the control logic only; it does not claim anything about the quality of real agents.

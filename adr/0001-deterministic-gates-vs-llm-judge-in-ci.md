# ADR 0001: Deterministic gates before any LLM judge in CI

## Status

Accepted.

## Context

A release pipeline for an LLM feature needs a pass or fail on every change. One option is to ask another model whether the output looks safe. That verdict can differ between two runs on the same input, costs money on every run, and cannot be reproduced by an auditor later. Several repositories in this design (`llm-adversarial-gate`, `rag-groundedness-gate`, `supply-chain-lockdown`) are offline, need no network and no key, and give the same answer for the same input.

## Decision

Every blocking check in CI is a deterministic program with a planted-failure suite: it must catch a known bad case and pass a known good control. A model-based judge may add a signal, but it never holds a veto and never overrides a deterministic gate. A guard that scores perfectly on its own author's cases is also scored on unseen cases with `blind-eval-harness`, which counts a crash or timeout as the guard's own flag.

## Alternatives considered

- Model judge as the only gate: flexible on open-ended text, but not reproducible and not free.
- Model judge as a tie-breaker that can pass what a gate blocked: turns every gate into a suggestion.
- Human review of every change: accurate, but does not scale to every prompt edit.

## Consequences

- A CI failure always names the rule that fired, so the fix is a code change, not a debate.
- Coverage is limited to what can be written as a rule. Anything else is out of scope for the gate and is named as a known gap, not hidden.
- The same inputs give the same verdict a year later, which lets the verdict be audited.

## Trade-offs

Rules miss paraphrases and new attack shapes that a model would generalize to. We accept lower recall in exchange for a verdict that is explainable, free to run and identical on rerun. The recall gap is measured on unseen cases and published, not argued away.

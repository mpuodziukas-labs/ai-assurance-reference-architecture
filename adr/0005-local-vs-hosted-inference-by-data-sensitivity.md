# ADR 0005: Local or hosted inference decided by data sensitivity

## Status

Accepted.

## Context

Hosted inference is usually cheaper and stronger per request. Local inference keeps data on hardware you control. Choosing by cost or quality alone puts sensitive text on the wrong side of the line. `sensitivity-egress-router` routes by class first and uses cost only among the destinations that class allows. `llm-data-boundary` adds a per-provider check using recorded attributes such as whether the provider trains on inputs, retention, region, contract and attestation date.

## Decision

The data class decides the destination set, and cost, latency and quality choose within that set. Classification looks at the data, not at the task. Text that matches a sensitive shape (secret key, personal identifier, health note about a person) goes local only. The capacity model in `capacity/` is run separately for the local and hosted paths with prices you supply, so the cost of the safe choice is visible before it is made.

## Alternatives considered

- Everything hosted with a contract: cheapest to run, but one mistake is not reversible.
- Everything local: safest, but caps quality and throughput for requests that carry no sensitive data.
- Let the model or the user choose per request: pushes a policy decision to the least reliable place.

## Consequences

- A local outage affects sensitive requests only, and those are refused, not rerouted.
- Provider attributes need a named owner and a refresh date, because a stale record is a DENY.
- Cost per request differs by class, and the cost model reports it for each path you describe.

## Trade-offs

We pay for local capacity that sits partly idle so that sensitive text has a place to go. Classification will sometimes route a benign prompt local; that false positive is accepted and counted rather than tuned away silently.

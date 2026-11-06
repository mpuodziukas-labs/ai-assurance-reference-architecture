# ADR 0002: Fail-closed egress

## Status

Accepted.

## Context

Once a prompt reaches a hosted destination it cannot be taken back. A router that picks the cheapest destination first can send a key, a personal identifier or a patient note to a vendor in one request. `sensitivity-egress-router` classifies first and picks the destination second, and `llm-data-boundary` decides per request from recorded provider attributes, with anything unknown, stale, contradictory or malformed treated as DENY.

## Decision

Every egress decision defaults to the safer outcome. Unknown class means local or refuse. A stale or missing provider record means DENY. If the local destination is down and the class requires local, the request is refused, not rerouted to a hosted destination. Fail-open is allowed only for a component that cannot cause data to leave or an unauthorized action to run. The release monitor's live drift and cost watching is the one such case in this design: if it is down, traffic continues on the last released version and no new version is promoted.

## Alternatives considered

- Fail-open with an alert: keeps the feature up, but the alert arrives after the data left.
- Fail-closed everywhere including monitoring: safest for data, but a monitor outage then takes the whole feature down.
- Redact everything and always allow: removes the decision, but redaction misses obfuscated forms.

## Consequences

- Some benign prompts are routed local or refused. The router's README reports this over-block count instead of hiding it.
- A provider attestation that goes stale blocks that provider until someone refreshes the record.
- Availability of the feature depends on the local destination being up for sensitive classes.

## Trade-offs

We trade availability and some false blocks for the guarantee that a sensitive class never reaches a hosted destination by default. The cost of a blocked benign prompt is a retry; the cost of a leaked prompt is permanent.

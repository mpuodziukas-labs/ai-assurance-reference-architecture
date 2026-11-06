# ADR 0006: Pre-action authorization for tools

## Status

Accepted.

## Context

An agent can call a tool with a host, file or shell command nobody approved, and the damage lands before anyone reads a log. A pattern scanner on the text of an injection loses to paraphrase. Three repositories split the problem: `pre-action-authorization` checks each call against an allowlist, `taint-flow-guard` blocks a plan whose tool choice or sensitive argument derives from untrusted data, and `attested-tool-results` accepts a result only with a valid, fresh, unseen receipt tied to a call the agent issued.

## Decision

A tool call runs only if all three agree, in this order: the plan passes the taint check, the call passes the allowlist, and the result passes receipt verification before it enters agent context. The shell class is an allowlist of commands, never a denylist of verbs. Any request that is malformed or in a class the policy does not know is denied. Tool manifests are scanned with `mcp-manifest-scan` before a server is trusted.

## Alternatives considered

- Denylist of dangerous verbs: short to write, bypassed by chaining, expansion and interpreters.
- Detect injection by wording only: loses to every new phrasing or language.
- Human approval for every call: safe, and too slow for autonomous work.

## Consequences

- A new tool or host needs a policy change before it works, which is the intended friction.
- The taint check depends on a policy that declares which arguments are sensitive; a wrong policy is a wrong verdict.
- A tool that cannot produce a receipt cannot be used on the attested path.

## Trade-offs

Three checks add latency to each call and three policies to maintain. We accept this because each check fails differently: wording changes defeat none of them, and a bypass of one still meets the others.

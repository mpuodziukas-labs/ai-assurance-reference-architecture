"""Tiny director/executor orchestrator over mock agents.

The director plans disjoint file lanes with token budgets. Each executor is a
plain function that mutates a copy of the workspace and returns the tokens it
claims to have used. The verifier does not trust the executor: it diffs the
workspace itself, compares usage to the lane budget and re-runs the lane check.
No network, no model calls.
"""
import posixpath
from dataclasses import dataclass, field


class PlanError(Exception):
    pass


@dataclass(frozen=True)
class Lane:
    name: str
    files: tuple
    budget: int
    check: object = field(compare=False)

    def __post_init__(self):
        if self.budget <= 0:
            raise PlanError("lane %s: budget must be > 0" % self.name)
        for f in self.files:
            norm = posixpath.normpath(f)
            if f.startswith("/") or norm.startswith("..") or norm != f:
                raise PlanError("lane %s: unsafe path %r" % (self.name, f))


@dataclass
class Verdict:
    accepted: bool
    reason: str
    tokens: int = 0


@dataclass
class Report:
    verdicts: dict
    workspace: dict
    tokens_used: int


class Director:
    def __init__(self, total_budget):
        self.total_budget = total_budget

    def _plan_check(self, lanes):
        if not lanes:
            raise PlanError("empty plan")
        seen = {}
        for lane in lanes:
            for f in lane.files:
                if f in seen:
                    raise PlanError("file %s owned by %s and %s" % (f, seen[f], lane.name))
                seen[f] = lane.name
        if sum(l.budget for l in lanes) > self.total_budget:
            raise PlanError("lane budgets exceed total budget")

    def run(self, lanes, agents, workspace=None):
        self._plan_check(lanes)
        merged = dict(workspace or {})
        verdicts = {}
        total = 0
        for lane in lanes:
            verdicts[lane.name] = self._verify(lane, agents, merged)
            if verdicts[lane.name].accepted:
                total += verdicts[lane.name].tokens
        return Report(verdicts, merged, total)

    def _verify(self, lane, agents, merged):
        agent = agents.get(lane.name)
        if agent is None:
            return Verdict(False, "missing-agent")
        before = dict(merged)
        scratch = dict(merged)
        try:
            used = agent(lane, scratch)
        except Exception:
            return Verdict(False, "agent-error")
        if used > lane.budget:
            return Verdict(False, "budget", used)
        touched = sorted(
            k for k in set(before) | set(scratch) if before.get(k) != scratch.get(k)
        )
        for path in touched:
            if path not in lane.files:
                return Verdict(False, "scope:" + path, used)
        if not lane.check(scratch):
            return Verdict(False, "check", used)
        merged.clear()
        merged.update(scratch)
        return Verdict(True, "ok", used)

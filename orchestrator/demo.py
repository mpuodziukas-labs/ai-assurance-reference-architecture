#!/usr/bin/env python3
"""Demo: two plans over mock agents. Exits 0 only if every verdict is the expected one."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from director import Director, Lane  # noqa: E402


def lanes():
    return [
        Lane("gate", ("src/gate.txt",), 100, lambda ws: ws.get("src/gate.txt") == "ok"),
        Lane("eval", ("src/eval.txt",), 100, lambda ws: ws.get("src/eval.txt") == "ok"),
        Lane("docs", ("docs/readme.txt",), 100, lambda ws: ws.get("docs/readme.txt") == "ok"),
    ]


def writer(path, used, value="ok", extra=None):
    def agent(lane, ws):
        ws[path] = value
        if extra:
            ws[extra] = "x"
        return used
    return agent


def show(title, report):
    print("== " + title)
    for name in sorted(report.verdicts):
        v = report.verdicts[name]
        print("%-6s %s %s" % (name, "ACCEPT" if v.accepted else "REJECT", v.reason))
    print("merged: " + ",".join(sorted(report.workspace)))
    print("tokens accepted: %d" % report.tokens_used)


def main():
    d = Director(total_budget=300)
    good = d.run(lanes(), {
        "gate": writer("src/gate.txt", 40),
        "eval": writer("src/eval.txt", 55),
        "docs": writer("docs/readme.txt", 20),
    })
    show("plan 1: all lanes in scope", good)
    bad = d.run(lanes(), {
        "gate": writer("src/gate.txt", 140),
        "eval": writer("src/eval.txt", 30, extra="docs/readme.txt"),
        "docs": writer("docs/readme.txt", 20, value="wrong"),
    })
    show("plan 2: budget breach, foreign touch, lying executor", bad)
    expect_good = {"gate": "ok", "eval": "ok", "docs": "ok"}
    expect_bad = {"gate": "budget", "eval": "scope:docs/readme.txt", "docs": "check"}
    got_good = {k: v.reason for k, v in good.verdicts.items()}
    got_bad = {k: v.reason for k, v in bad.verdicts.items()}
    if got_good != expect_good or got_bad != expect_bad or bad.workspace:
        print("DEMO MISMATCH")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Lint ARCHITECTURE.md and adr/*.md.

Checks: every ADR has all six sections; every component row names a repo from
the allowed list; every trust boundary in a diagram appears in the component
table; every mermaid block is balanced and uses only declared node ids.
Usage: arch-lint.py [--root DIR]. Exit 0 clean, 1 on any finding, 2 on usage.
"""
import glob
import os
import re
import sys

ALLOWED = {
    "llm-adversarial-gate", "rag-groundedness-gate", "llm-data-boundary",
    "context-injection-firewall", "mcp-manifest-scan", "pre-action-authorization",
    "attested-tool-results", "agent-trace-receipts", "llmops-release-monitor",
    "prompt-regression-suite", "blind-eval-harness", "supply-chain-lockdown",
    "sensitivity-egress-router", "ai-risk-register", "taint-flow-guard",
    "k8s-deploy-gate",
}
SECTIONS = ["Status", "Context", "Decision", "Alternatives considered",
            "Consequences", "Trade-offs"]
POSTURES = {"fail-open", "fail-closed"}
SHAPES = [r'\(\([^)]*\)\)', r'\[[^\]]*\]', r'\([^)]*\)', r'\{[^}]*\}']
ARROWS = r'\s*(?:-->|-\.->|==>|-\.-|---)\s*'
BLOCK_OPEN = ("loop", "alt", "opt", "par", "rect", "critical", "break")


def lint_adrs(root):
    errs = []
    files = sorted(glob.glob(os.path.join(root, "adr", "[0-9][0-9][0-9][0-9]-*.md")))
    if not files:
        return ["no ADR files found under adr/"]
    for path in files:
        text = open(path, encoding="utf-8").read()
        heads = {m.group(1).strip() for m in re.finditer(r'^## (.+?)\s*$', text, re.M)}
        for sec in SECTIONS:
            if sec not in heads:
                errs.append("%s: missing section '%s'" % (os.path.basename(path), sec))
    return errs


def mermaid_blocks(text):
    return re.findall(r'```mermaid\n(.*?)```', text, re.S)


def check_mermaid(idx, body):
    tag = "mermaid block %d" % idx
    errs = []
    lines = [l.strip() for l in body.splitlines()
             if l.strip() and not l.strip().startswith("%%")]
    if not lines:
        return [tag + ": empty"]
    for a, b in ("[]", "()", "{}"):
        if body.count(a) != body.count(b):
            errs.append("%s: unbalanced %s%s" % (tag, a, b))
    if body.count('"') % 2:
        errs.append(tag + ": odd number of quotes")
    head = lines[0]
    if head.startswith(("flowchart", "graph")):
        errs += check_flow(tag, lines[1:])
    elif head == "sequenceDiagram":
        errs += check_seq(tag, lines[1:])
    else:
        errs.append("%s: unknown diagram type '%s'" % (tag, head))
    return errs


def check_flow(tag, lines):
    errs, declared, edges, depth = [], set(), [], 0
    for line in lines:
        m = re.match(r'subgraph\s+(\w+)', line)
        if m:
            declared.add(m.group(1))
            depth += 1
            continue
        if line == "end":
            depth -= 1
            if depth < 0:
                errs.append(tag + ": 'end' without subgraph")
                depth = 0
            continue
        flat = re.sub(r'"[^"]*"', '""', line)
        for d in re.finditer(r'\b([A-Za-z_]\w*)\s*(?=\[|\(|\{)', flat):
            declared.add(d.group(1))
        for pat in SHAPES:
            flat = re.sub(pat, "", flat)
        flat = re.sub(r'\|[^|]*\|', "", flat)
        parts = re.split(ARROWS, flat.strip())
        if len(parts) > 1:
            for part in parts:
                for tok in part.split("&"):
                    edges.append(tok.strip())
        else:
            tok = flat.strip()
            if not re.fullmatch(r'\w+', tok):
                errs.append("%s: cannot parse line '%s'" % (tag, line))
    if depth != 0:
        errs.append(tag + ": subgraph without end")
    for tok in edges:
        if not re.fullmatch(r'\w+', tok):
            errs.append("%s: bad edge endpoint '%s'" % (tag, tok))
        elif tok not in declared:
            errs.append("%s: unknown node id '%s'" % (tag, tok))
    return errs


def check_seq(tag, lines):
    errs, declared, msgs, depth = [], set(), [], 0
    for line in lines:
        m = re.match(r'participant\s+(\w+)', line)
        if m:
            declared.add(m.group(1))
            continue
        m = re.match(r'(\w+)\s*--?>>\s*(\w+)\s*:', line)
        if m:
            msgs.append((m.group(1), m.group(2)))
            continue
        first = line.split()[0]
        if first in BLOCK_OPEN:
            depth += 1
        elif first == "end":
            depth -= 1
        elif first not in ("Note", "autonumber", "else", "and"):
            errs.append("%s: cannot parse line '%s'" % (tag, line))
    if depth != 0:
        errs.append(tag + ": block without end")
    for a, b in msgs:
        for n in (a, b):
            if n not in declared:
                errs.append("%s: unknown participant '%s'" % (tag, n))
    return errs


def component_rows(text):
    rows, head, in_table = [], None, False
    for line in text.splitlines():
        if not line.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        low = [c.lower() for c in cells]
        if head is None:
            if "component" in low and "repo" in low:
                head, in_table = low, True
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return head, rows


def lint_architecture(root):
    path = os.path.join(root, "ARCHITECTURE.md")
    if not os.path.isfile(path):
        return ["ARCHITECTURE.md not found"]
    text = open(path, encoding="utf-8").read()
    errs = []
    head, rows = component_rows(text)
    if head is None or not rows:
        return ["component table not found or empty"]
    need = ("repo", "boundary", "posture")
    if any(n not in head for n in need):
        return ["component table needs columns: repo, boundary, posture"]
    ri, bi, pi = (head.index(n) for n in need)
    table_tbs = set()
    for r in rows:
        if len(r) != len(head):
            errs.append("table row has %d cells, expected %d: %s" % (len(r), len(head), r[0]))
            continue
        repo = r[ri].strip("`").strip()
        if repo not in ALLOWED:
            errs.append("row '%s' names unknown repo '%s'" % (r[0], repo))
        if r[pi] not in POSTURES:
            errs.append("row '%s' posture '%s' is not fail-open or fail-closed" % (r[0], r[pi]))
        table_tbs |= set(re.findall(r'TB\d+', r[bi]))
    blocks = mermaid_blocks(text)
    if not blocks:
        errs.append("no mermaid blocks found")
    diagram_tbs = set()
    for i, body in enumerate(blocks, 1):
        errs += check_mermaid(i, body)
        diagram_tbs |= set(re.findall(r'\bTB\d+\b', body))
    if blocks and not diagram_tbs:
        errs.append("no trust boundary ids (TBn) found in diagrams")
    for tb in sorted(diagram_tbs - table_tbs):
        errs.append("trust boundary %s is in a diagram but not in the component table" % tb)
    return errs


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if len(argv) == 3 and argv[1] == "--root":
        root = argv[2]
    elif len(argv) != 1:
        print("usage: arch-lint.py [--root DIR]", file=sys.stderr)
        return 2
    errs = lint_adrs(root) + lint_architecture(root)
    for e in errs:
        print("FAIL: " + e)
    if errs:
        return 1
    n_adr = len(glob.glob(os.path.join(root, "adr", "[0-9][0-9][0-9][0-9]-*.md")))
    print("arch-lint OK: %d ADRs, all sections present, diagrams and table consistent" % n_adr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from director import Director, Lane, PlanError  # noqa: E402


def lane_a(**kw):
    d = dict(name="a", files=("src/a.txt",), budget=100,
             check=lambda ws: ws.get("src/a.txt") == "done")
    d.update(kw)
    return Lane(**d)


def lane_b(**kw):
    d = dict(name="b", files=("src/b.txt",), budget=100,
             check=lambda ws: ws.get("src/b.txt") == "done")
    d.update(kw)
    return Lane(**d)


def good(path, used):
    def agent(lane, ws):
        ws[path] = "done"
        return used
    return agent


def test_accept_path_merges_both_lanes():
    rep = Director(total_budget=300).run(
        [lane_a(), lane_b()],
        {"a": good("src/a.txt", 40), "b": good("src/b.txt", 60)},
    )
    assert rep.verdicts["a"].accepted and rep.verdicts["b"].accepted
    assert rep.workspace == {"src/a.txt": "done", "src/b.txt": "done"}
    assert rep.tokens_used == 100


def test_reject_budget_breach_and_do_not_merge():
    rep = Director(total_budget=300).run(
        [lane_a(), lane_b()],
        {"a": good("src/a.txt", 101), "b": good("src/b.txt", 10)},
    )
    assert not rep.verdicts["a"].accepted
    assert rep.verdicts["a"].reason == "budget"
    assert rep.verdicts["b"].accepted
    assert "src/a.txt" not in rep.workspace


def test_budget_exactly_at_cap_is_accepted():
    rep = Director(total_budget=300).run(
        [lane_a()], {"a": good("src/a.txt", 100)})
    assert rep.verdicts["a"].accepted


def test_reject_touching_another_lanes_file():
    def trespass(lane, ws):
        ws["src/a.txt"] = "done"
        ws["src/b.txt"] = "stolen"
        return 5
    rep = Director(total_budget=300).run(
        [lane_a(), lane_b()],
        {"a": trespass, "b": good("src/b.txt", 5)},
    )
    assert not rep.verdicts["a"].accepted
    assert rep.verdicts["a"].reason == "scope:src/b.txt"
    assert rep.workspace["src/b.txt"] == "done"
    assert "src/a.txt" not in rep.workspace


def test_reject_touching_unowned_file():
    def stray(lane, ws):
        ws["src/a.txt"] = "done"
        ws["other/x.txt"] = "x"
        return 5
    rep = Director(total_budget=300).run([lane_a()], {"a": stray})
    assert rep.verdicts["a"].reason == "scope:other/x.txt"


def test_deleting_a_foreign_file_is_a_touch():
    def deleter(lane, ws):
        ws["src/a.txt"] = "done"
        del ws["seed.txt"]
        return 5
    rep = Director(total_budget=300).run(
        [lane_a()], {"a": deleter}, workspace={"seed.txt": "s"})
    assert rep.verdicts["a"].reason == "scope:seed.txt"
    assert rep.workspace == {"seed.txt": "s"}


def test_reject_when_verifier_rerun_check_fails_despite_agent_claim():
    def liar(lane, ws):
        ws["src/a.txt"] = "wrong"
        return 5
    rep = Director(total_budget=300).run([lane_a()], {"a": liar})
    assert rep.verdicts["a"].reason == "check"
    assert not rep.verdicts["a"].accepted


def test_reject_agent_exception_fail_closed():
    def boom(lane, ws):
        raise RuntimeError("x")
    rep = Director(total_budget=300).run([lane_a()], {"a": boom})
    assert rep.verdicts["a"].reason == "agent-error"


def test_reject_missing_agent():
    rep = Director(total_budget=300).run([lane_a()], {})
    assert rep.verdicts["a"].reason == "missing-agent"


def test_plan_error_overlapping_files():
    with pytest.raises(PlanError):
        Director(total_budget=300).run(
            [lane_a(), lane_b(files=("src/a.txt",))], {})


def test_plan_error_lane_budgets_exceed_total():
    with pytest.raises(PlanError):
        Director(total_budget=150).run([lane_a(), lane_b()], {})


def test_plan_error_empty_plan():
    with pytest.raises(PlanError):
        Director(total_budget=10).run([], {})


@pytest.mark.parametrize("bad", ["/abs.txt", "../up.txt", "a/../../b.txt"])
def test_lane_rejects_unsafe_paths(bad):
    with pytest.raises(PlanError):
        lane_a(files=(bad,))


def test_lane_rejects_nonpositive_budget():
    with pytest.raises(PlanError):
        lane_a(budget=0)


def test_demo_runs_and_is_deterministic():
    cmd = [sys.executable, os.path.join(HERE, "demo.py")]
    a = subprocess.run(cmd, capture_output=True, text=True)
    b = subprocess.run(cmd, capture_output=True, text=True)
    assert a.returncode == 0, a.stdout + a.stderr
    assert a.stdout == b.stdout
    assert "REJECT" in a.stdout and "ACCEPT" in a.stdout

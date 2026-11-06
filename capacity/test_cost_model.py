import copy
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cost_model  # noqa: E402

BASE = {
    "requests_per_day": 1000,
    "days_per_month": 30,
    "tokens_in": 1000,
    "tokens_out": 500,
    "price_per_million_in": 2.0,
    "price_per_million_out": 4.0,
    "cache_hit_rate": 0.5,
    "cache_cost_per_request": 0.0001,
    "cache_fixed_monthly": 30.0,
    "slo_ms": 2000,
    "stages": [
        {"name": "retrieve", "p95_ms": 120, "budget_ms": 200},
        {"name": "model", "p95_ms": 1400, "budget_ms": 1500},
        {"name": "verify", "p95_ms": 80, "budget_ms": 150},
    ],
}


def params(**over):
    p = copy.deepcopy(BASE)
    p.update(over)
    return p


def test_hand_derived_cost():
    r = cost_model.compute(params())
    # per model call: 1000*2/1e6 + 500*4/1e6 = 0.004
    assert r["cost_per_model_call"] == pytest.approx(0.004)
    # monthly: 30000 * (0.5*0.004 + 0.5*0.0001) + 30 = 91.5
    assert r["monthly_cost"] == pytest.approx(91.5)
    assert r["cost_per_request"] == pytest.approx(91.5 / 30000)
    assert r["monthly_cost_no_cache"] == pytest.approx(120.0)


def test_break_even_cache_hit_rate():
    r = cost_model.compute(params())
    assert r["break_even_cache_hit_rate"] == pytest.approx(30.0 / (30000 * 0.0039))


def test_break_even_none_when_never_pays_off():
    r = cost_model.compute(params(cache_fixed_monthly=100000.0))
    assert r["break_even_cache_hit_rate"] is None


def test_break_even_none_when_cache_not_cheaper():
    r = cost_model.compute(params(cache_cost_per_request=0.01))
    assert r["break_even_cache_hit_rate"] is None


def test_latency_budget_within_slo():
    r = cost_model.compute(params())
    assert r["total_p95_ms"] == 1600
    assert r["slo_ok"] is True
    assert [s["headroom_ms"] for s in r["stages"]] == [80, 100, 70]
    assert all(s["within_budget"] for s in r["stages"])


def test_latency_budget_breach_flagged():
    p = params()
    p["stages"][1]["p95_ms"] = 1900
    r = cost_model.compute(p)
    assert r["stages"][1]["within_budget"] is False
    assert r["slo_ok"] is False


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_cache_rate_out_of_range_rejected(bad):
    with pytest.raises(ValueError):
        cost_model.compute(params(cache_hit_rate=bad))


@pytest.mark.parametrize(
    "key",
    ["requests_per_day", "tokens_in", "tokens_out", "price_per_million_in",
     "price_per_million_out", "cache_fixed_monthly", "slo_ms"],
)
def test_negative_inputs_rejected(key):
    with pytest.raises(ValueError):
        cost_model.compute(params(**{key: -1}))


def test_missing_key_rejected():
    p = params()
    del p["tokens_in"]
    with pytest.raises(ValueError):
        cost_model.compute(p)


def test_negative_stage_latency_rejected():
    p = params()
    p["stages"][0]["p95_ms"] = -5
    with pytest.raises(ValueError):
        cost_model.compute(p)


def test_cli_on_example_is_deterministic():
    ex = os.path.join(HERE, "example.yaml")
    cmd = [sys.executable, os.path.join(HERE, "cost_model.py"), ex]
    a = subprocess.run(cmd, capture_output=True, text=True)
    b = subprocess.run(cmd, capture_output=True, text=True)
    assert a.returncode == 0, a.stderr
    assert a.stdout == b.stdout
    assert "monthly_cost" in a.stdout


def test_cli_rejects_bad_yaml(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("requests_per_day: 10\ncache_hit_rate: -1\n")
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "cost_model.py"), str(bad)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0

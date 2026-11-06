#!/usr/bin/env python3
"""Deterministic token, cost and latency model.

Usage: python3 capacity/cost_model.py PARAMS.yaml
Prices are parameters you supply. Nothing here knows a price.
"""
import json
import sys

NON_NEGATIVE = (
    "requests_per_day", "days_per_month", "tokens_in", "tokens_out",
    "price_per_million_in", "price_per_million_out",
    "cache_cost_per_request", "cache_fixed_monthly", "slo_ms",
)


def _validate(p):
    for key in NON_NEGATIVE + ("cache_hit_rate", "stages"):
        if key not in p:
            raise ValueError("missing key: " + key)
    for key in NON_NEGATIVE:
        if not isinstance(p[key], (int, float)) or p[key] < 0:
            raise ValueError(key + " must be a number >= 0")
    rate = p["cache_hit_rate"]
    if not 0.0 <= rate <= 1.0:
        raise ValueError("cache_hit_rate must be within 0..1")
    if not p["stages"]:
        raise ValueError("stages must not be empty")
    for s in p["stages"]:
        for k in ("name", "p95_ms", "budget_ms"):
            if k not in s:
                raise ValueError("stage missing key: " + k)
        if s["p95_ms"] < 0 or s["budget_ms"] < 0:
            raise ValueError("stage latencies must be >= 0")


def compute(p):
    _validate(p)
    n = p["requests_per_day"] * p["days_per_month"]
    h = p["cache_hit_rate"]
    call = (p["tokens_in"] * p["price_per_million_in"]
            + p["tokens_out"] * p["price_per_million_out"]) / 1e6
    hit = p["cache_cost_per_request"]
    fixed = p["cache_fixed_monthly"]
    monthly = n * ((1 - h) * call + h * hit) + fixed
    saving_per_hit = call - hit
    if saving_per_hit > 0 and n > 0:
        be = fixed / (n * saving_per_hit)
        be = be if be <= 1.0 else None
    else:
        be = None
    stages = [{
        "name": s["name"],
        "p95_ms": s["p95_ms"],
        "budget_ms": s["budget_ms"],
        "headroom_ms": s["budget_ms"] - s["p95_ms"],
        "within_budget": s["p95_ms"] <= s["budget_ms"],
    } for s in p["stages"]]
    total = sum(s["p95_ms"] for s in p["stages"])
    return {
        "requests_per_month": n,
        "cost_per_model_call": round(call, 9),
        "monthly_cost": round(monthly, 6),
        "monthly_cost_no_cache": round(n * call, 6),
        "cost_per_request": round(monthly / n, 9) if n else None,
        "break_even_cache_hit_rate": None if be is None else round(be, 6),
        "stages": stages,
        "total_p95_ms": total,
        "slo_ms": p["slo_ms"],
        "slo_ok": total <= p["slo_ms"] and all(s["within_budget"] for s in stages),
        "note": "total_p95_ms is the sum of stage p95 values, a conservative upper bound",
    }


def main(argv):
    if len(argv) != 2:
        print("usage: cost_model.py PARAMS.yaml", file=sys.stderr)
        return 2
    import yaml
    with open(argv[1]) as f:
        params = yaml.safe_load(f)
    try:
        result = compute(params)
    except ValueError as e:
        print("REJECT: " + str(e), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

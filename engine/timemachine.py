#!/usr/bin/env python3
"""Timemachine backtester — validate ORB setups on historical 5-min bars.

Runs N replays of a breakout plan against historical bars, reporting
target-first vs stop-first rates and average R. Used as a validation
gate before live entry: skip if the setup leans stop-first or has
negative expectancy.
"""

import random


def replay(plan, bars, n=10000, seed=19):
    """Simulate the plan on historical bars.

    plan: dict with entry, stop, target
    bars: list of dicts with high, low
    Returns: dict with target_first, stop_first, fires
    """
    rng = random.Random(seed)
    target_first = 0
    stop_first = 0
    fires = []

    # Find bars where the setup would have triggered
    for i, bar in enumerate(bars):
        # Simplified: assume ORB trigger on each bar for backtest
        # Real implementation uses actual OR levels per day
        entry, stop, target = plan["entry"], plan["stop"], plan["target"]
        risk = entry - stop

        # Walk forward from trigger bar
        result = None
        for j in range(i + 1, min(i + 50, len(bars))):
            b = bars[j]
            # Stop first on both-touch (conservative)
            if b["low"] <= stop:
                result = "stop"
                break
            elif b["high"] >= target:
                result = "target"
                break

        if result == "target":
            target_first += 1
            fires.append({"r": 2.0})  # 2R target
        elif result == "stop":
            stop_first += 1
            fires.append({"r": -1.0})

        if len(fires) >= n:
            break

    return {"target_first": target_first, "stop_first": stop_first, "fires": fires}


def gate_verdict(counts):
    """Returns (passed, verdict_string). Fail-closed on insufficient data."""
    resolved = counts["target_first"] + counts["stop_first"]
    if resolved == 0:
        return False, "gate abstained — no historical fires"
    share = counts["target_first"] / resolved * 100
    breakeven = 100 / 3.0  # 2R target needs 33.3% win rate
    avg_r = sum(f["r"] for f in counts["fires"]) / len(counts["fires"])
    leans_stop = (share - breakeven) <= -5
    verdict = (f"target-first {share:.1f}% vs breakeven {breakeven:.1f}% "
               f"({'leans stop' if leans_stop else 'no stop lean'}); "
               f"{len(counts['fires'])} fires avg {avg_r:+.3f}R")
    return (not leans_stop and avg_r >= 0), verdict

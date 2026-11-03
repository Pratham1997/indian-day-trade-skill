#!/usr/bin/env python3
"""Hero scoring — catalyst-driven watchlist.

Scores names on a rubric; top scorers (≥4) get dedicated tracking
and reduced-risk entries. Hard exclusions keep out circuit-locked,
illiquid, or results-day names.

Rubric:
    +3  filed catalyst ≤24h
    +3  promoter/insider BUY ≤7d
    +2  news cluster ≥5 articles/24h
    +2  crowd spike (shared award, never stacks)
    +1  credible bulk/block buy
    −2  euphoria (overbought + hype)
    −3  filed negative (downgrade, fraud, regulatory)
"""


def score_hero(signals):
    """signals: dict of boolean flags. Returns (score, is_hero)."""
    score = 0
    if signals.get("filed_catalyst_24h"):  score += 3
    if signals.get("promoter_buy_7d"):     score += 3
    if signals.get("news_cluster"):        score += 2
    if signals.get("crowd_spike"):         score += 2
    if signals.get("bulk_buy"):            score += 1
    if signals.get("euphoria"):            score -= 2
    if signals.get("filed_negative"):      score -= 3
    return score, score >= 4


def is_excluded(symbol, circuit_lock=False, illiquid=False, results_soon=False):
    """Hard exclusions — never a hero regardless of score."""
    return circuit_lock or illiquid or results_soon

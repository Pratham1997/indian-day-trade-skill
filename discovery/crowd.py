#!/usr/bin/env python3
"""Crowd signals — Telegram momentum + Google Trends spikes.

Social attention as a context signal, not a trigger.
One shared award across sources (never double-count the same spike).
"""


def telegram_momentum(channel_posts, window_hours=24):
    """Mentions per hour vs 7-day baseline. Returns spike ratio."""
    if not channel_posts:
        return 0.0
    recent = sum(1 for p in channel_posts if p["age_hours"] <= window_hours)
    baseline = len(channel_posts) / 7 / 24  # per-hour baseline
    return recent / max(baseline, 0.1)


def trends_spike(current_interest, baseline_interest):
    """Google Trends 0-100 vs baseline. Returns True on 3x+ spike."""
    return current_interest >= 3 * max(baseline_interest, 5)


def crowd_score(symbol, telegram_ratio=0.0, trends_spike=False):
    """Single shared score — a spike in either source counts once."""
    spike = telegram_ratio >= 3.0 or trends_spike
    return 1 if spike else 0

#!/usr/bin/env python3
"""Dual-feed router — Upstox primary, Yahoo fallback.

For live intraday (1d/5m): try Upstox first, fall back to Yahoo on failure.
For historical ranges: Yahoo directly.
"""

try:
    from .upstox_feed import get_5min_bars as _upstox_bars
    _UPSTOX_OK = True
except ImportError:
    _UPSTOX_OK = False

from .yahoo_feed import get_bars as _yahoo_bars


def get_bars(symbol, range_="1d", interval="5m"):
    """(meta, bars) — Upstox primary for live, Yahoo fallback + historical."""
    if _UPSTOX_OK and range_ == "1d" and interval == "5m":
        try:
            bars = _upstox_bars(symbol)
            return {"source": "upstox", "symbol": symbol}, bars
        except Exception:
            pass  # fall through to Yahoo
    return _yahoo_bars(symbol, range_, interval)

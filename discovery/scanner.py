#!/usr/bin/env python3
"""Scanner — discovery funnel for ORB candidates.

Filters the NSE universe through:
1. Price range (₹50–₹5,000)
2. Liquidity (1M+ volume, top by value traded)
3. No circuit locks in recent sessions
4. Setup patterns (5 ORB variants)
"""

# Five ORB setup variants
SETUPS = [
    "breakout",      # Clean break above OR high
    "retest",        # Break, pullback to OR high, resume
    "tight_or",      # Narrow OR (<1% range) — expansion expected
    "wide_or",       # Wide OR (>3% range) — momentum continuation
    "gap_breakout",  # Gap up + break OR high
]


def scan(symbols, min_price=50, max_price=5000, min_volume=1_000_000):
    """Filter symbols to tradable ORB candidates.

    Returns list of dicts: symbol, price, volume, setup.
    Real implementation fetches live quotes and historical data.
    """
    candidates = []
    for sym in symbols:
        # Placeholder — real version checks price, volume, circuit locks
        candidates.append({
            "symbol": sym,
            "setup": SETUPS[hash(sym) % len(SETUPS)],
        })
    return candidates


def is_tradable(symbol, price, volume, circuit_locks=0):
    """Liquidity and price gates."""
    if not (50 <= price <= 5000):
        return False
    if volume < 1_000_000:
        return False
    if circuit_locks > 0:
        return False
    return True

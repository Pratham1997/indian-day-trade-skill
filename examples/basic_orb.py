#!/usr/bin/env python3
"""Minimal ORB example — fetch today's bars, find a breakout, paper-trade it.

Usage:
    export UPSTOX_TOKEN="your-token"
    python examples/basic_orb.py RELIANCE
"""

import sys
sys.path.insert(0, "src")

from upstox_feed import get_5min_bars
from ledger import Ledger


def main(symbol):
    bars = get_5min_bars(symbol)
    print(f"{symbol}: {len(bars)} 5-min bars")

    # Opening range: first three bars (09:15, 09:20, 09:25)
    or_high = max(b["high"] for b in bars[:3])
    or_low = min(b["low"] for b in bars[:3])
    print(f"OR: {or_low:.2f} - {or_high:.2f}")

    ledger = Ledger(capital=50000.0)

    # Find first bar closing above OR high (from 09:35 onward)
    for bar in bars[4:]:
        if bar["close"] > or_high:
            entry = bar["close"]
            stop = round((or_high + or_low) / 2, 2)
            target = round(entry + 2 * (entry - stop), 2)
            pos = ledger.open_trade(symbol, entry, stop, target)
            print(f"ENTRY {pos['shares']} @ {entry:.2f} | stop {stop:.2f} | target {target:.2f} | risk {pos['risk_pct']}%")
            break
    else:
        print("No trigger today.")
        return

    # Adjudicate on remaining bars
    for bar in bars[bars.index(bar) + 1:]:
        pos = ledger.open_position
        if not pos:
            break
        if bar["low"] <= pos["stop"]:
            t = ledger.close_trade(pos["stop"], "stop")
            print(f"STOPPED @ {pos['stop']:.2f} | PnL {t['pnl']:+.2f} ({t['r']:+.3f}R)")
            break
        elif bar["high"] >= pos["target"]:
            t = ledger.close_trade(pos["target"], "target")
            print(f"TARGET @ {pos['target']:.2f} | PnL {t['pnl']:+.2f} ({t['r']:+.3f}R)")
            break

    print("Summary:", ledger.summary())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "RELIANCE")

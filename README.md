# indian-day-trade-skill

Production-grade paper-trading infrastructure for NSE day trading. Built for systematic Opening Range Breakout strategies with dual-feed market data, crash-safe execution, and per-lane risk management.

> **This is engineering infrastructure, not a profitable strategy.** It demonstrates how to build reliable trading systems for India's market structure — an underserved niche in open-source trading tools.

## Quick start

```bash
pip install -r requirements.txt
export UPSTOX_TOKEN="your-analytics-token"  # never commit this
python examples/basic_orb.py
```

## What's inside

- **`SKILL.md`** — The complete skill definition: NSE structure, data sources, strategy, risk, reliability patterns
- **`src/upstox_feed.py`** — Upstox feed adapter (1-min → 5-min aggregation, Cloudflare-safe)
- **`src/feed.py`** — Dual-feed router (Upstox primary, Yahoo fallback)
- **`src/ledger.py`** — Paper ledger with per-lane capital and risk dial-down
- **`src/engine.py`** — ORB engine (opening range, triggers, validation gate, adjudication)
- **`docs/`** — Architecture and setup guides
- **`examples/`** — Runnable examples

## Key design decisions

1. **Dual feed:** Upstox primary (proper API, rate limits) with Yahoo fallback. Survives throttling.
2. **Fail-closed gate:** Validation failures veto instead of crashing.
3. **Exact restart:** Crash recovery without duplicate entries or stale exits.
4. **Paper-first:** No broker integration. Virtual ledger, real market data.

## NSE specifics

- Session: 09:15–15:30 IST
- Opening range: 09:15–09:30 (first three 5-min bars)
- Upstox intraday: 1-minute only — aggregate to 5-minute
- Cloudflare requires browser User-Agent on Upstox API calls

## License

MIT — see LICENSE.

## Disclaimer

Educational purposes only. Not financial advice. Paper-trade before considering live capital.

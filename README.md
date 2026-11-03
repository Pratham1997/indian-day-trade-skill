# indian-day-trade-skill

Production-grade **paper-trading infrastructure** for NSE (National Stock Exchange of India) day trading. Systematic Opening Range Breakout (ORB) with dual-feed market data, crash-safe execution, backtest validation gates, and per-lane risk management.

> **This is engineering infrastructure, not a profitable strategy.** It demonstrates how to build *reliable* trading systems: feed failover under throttling, exact-restart recovery after crashes, a 10,000-replay backtest gate before every entry, and a paper ledger with full audit trails. Most open-source trading tools are US-focused; this is built for India's market structure from the ground up.

📖 **[Full architecture →](docs/architecture.md)** — the complete pipeline: sources → discovery → validation → execution → settlement, with data-flow diagrams.

## Why Upstox?

The feed question is the hardest part of retail Indian market data. Here's the reasoning:

- **Free, no auth wall for the basics:** Upstox offers a read-only Analytics Token (1-year validity, free with a demat account). No monthly subscription, no credit card.
- **Real intraday candles:** 1-minute candles via a documented REST API — not scraped, not delayed beyond normal exchange feed latency.
- **Sane rate limits:** 50 requests/sec, 500/min, 2000/30min. Enough to poll ~90 symbols every 60 seconds without hitting walls.
- **Yahoo as fallback:** Yahoo Finance (`*.NS`) needs no auth and works for historical ranges, but it throttles aggressively under sustained polling (token-bucket, walls after ~30 min of heavy use). So Yahoo is the *fallback* for live bars and the *primary* for historical backfill — each feed doing what it's best at.

**The Cloudflare gotcha:** Upstox's WAF bans Python's default `urllib` User-Agent (HTTP 403, Error 1010). Every request must carry a browser User-Agent. This is the kind of thing that costs you an afternoon — it's handled in [`feed/upstox_feed.py`](feed/upstox_feed.py).

Alternatives evaluated and rejected: Kite Connect (₹2,000/mo), DhanHQ (₹499/mo), Groww (₹499/mo), Twelve Data free tier (800 credits/day — too thin), Alpha Vantage (25 req/day).

## Repository structure

```
├── feed/                    # Market data
│   ├── upstox_feed.py       # Upstox primary — 1m candles → 5m bars
│   ├── yahoo_feed.py        # Yahoo fallback + historical
│   └── router.py            # Dual-feed router (Upstox → Yahoo)
├── engine/                  # Execution
│   ├── ledger.py            # Paper P&L, position sizing, risk guards
│   └── timemachine.py       # Backtest gate — 10k replays before entry
├── discovery/               # Idea generation
│   ├── scanner.py           # NSE universe → ORB candidates (5 setups)
│   ├── sentiment.py         # English + Hinglish lexicon scorers
│   └── crowd.py             # Telegram + Google Trends signals
├── data/                    # Reference data
│   ├── nse_official.py      # Bhavcopy EOD settlement referee
│   └── results_calendar.py  # Earnings blocklist
├── docs/
│   ├── architecture.md      # Full infrastructure explained
│   └── setup.md             # Upstox token setup guide
└── examples/
    └── basic_orb.py         # Minimal runnable ORB example
```

## How it works

1. **Discovery** — the scanner narrows ~1,000 liquid NSE names to ORB candidates; sentiment and crowd signals add context.
2. **Validation** — every setup replays 10,000 times on 60 days of 5-minute history. Entry only if target-first rate beats breakeven *and* average R ≥ 0. The gate **fails closed**: no data → no trade.
3. **Execution** — opening range 09:15–09:30 IST, trigger on first close above OR high, stop at OR midpoint, 2R target. Polls every 60s.
4. **Risk** — 1% per trade (0.5% after 3 consecutive losses), max 3 trades/day, 1 open position, flat by 15:20 IST.
5. **Settlement** — Bhavcopy official closes are the price of record; the paper ledger reconciles every event.

## Quick start

```bash
# 1. Get a free Upstox Analytics Token (see docs/setup.md)
export UPSTOX_TOKEN="your-token"   # never commit this

# 2. Run the minimal example
python examples/basic_orb.py RELIANCE
```

## Relevant links

- [Upstox API documentation](https://upstox.com/developer/api-documentation/)
- [Upstox instrument master (NSE)](https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz)
- [NSE India](https://www.nseindia.com/) — official exchange, Bhavcopy downloads
- [NSE market timings](https://www.nseindia.com/trade/market-timings)
- [SKILL.md](SKILL.md) — skill definition for AI agents

## Status & roadmap

Active development. The system runs daily paper-trading sessions; components are extracted here as they stabilise. Planned: full engine loop, prep-session orchestration, shadow-tracking analytics.

## Disclaimer

Educational infrastructure. Not financial advice. Past paper performance does not predict future results. Paper-trade before considering live capital.

## License

MIT — see [LICENSE](LICENSE).

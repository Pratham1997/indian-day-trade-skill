# indian-day-trade-skill

Production-grade **paper-trading infrastructure** for NSE (National Stock Exchange of India) day trading. Systematic Opening Range Breakout (ORB) with dual-feed market data, crash-safe execution, backtest validation gates, and per-lane risk management.

> **This is engineering infrastructure, not a profitable strategy.** It demonstrates how to build *reliable* trading systems: feed failover under throttling, exact-restart recovery after crashes, a 10,000-replay backtest gate before every entry, and a paper ledger with full audit trails. Most open-source trading tools are US-focused; this is built for India's market structure from the ground up.

*Keywords: algorithmic trading, NSE, National Stock Exchange of India, intraday trading, day trading, paper trading, backtesting, market data API, Python trading bot, Indian stock market, systematic trading, quantitative trading, ORB strategy, opening range breakout, Upstox API, Yahoo Finance, risk management, portfolio*

📖 **[Full architecture →](docs/architecture.md)** — the complete pipeline: sources → discovery → validation → execution → settlement, with data-flow diagrams, failure modes, and design decisions.

## Data feed options

Pick the feed that fits your setup. The router (`feed/router.py`) defaults to Upstox → Yahoo fallback.

| Feed | Cost | One-line pro |
|------|------|--------------|
| **Upstox** | Free (Analytics Token, 1-yr, read-only) | Proper REST API with 1-min candles and sane rate limits — best free option |
| **Yahoo Finance** | Free, no auth | Zero setup, works for historical backfill — throttles under sustained live polling |
| **Kite Connect** | ₹2,000/mo | Official Zerodha API, reliable — expensive for paper trading |
| **Groww** | ₹499/mo + GST | Clean API — paid tier only for market data |
| **DhanHQ** | ₹499/mo + tax | Good API — paid tier only |
| **Angel One SmartAPI** | Free | Free with account — workable backup |
| **Twelve Data** | Free tier: 800 credits/day | Global coverage — too thin for intraday NSE polling |
| **Alpha Vantage** | Free tier: 25 req/day | Simple — unusable for live polling |

**Gotcha:** Upstox's Cloudflare WAF bans Python's default `urllib` User-Agent (HTTP 403). Every request must carry a browser User-Agent — handled in [`feed/upstox_feed.py`](feed/upstox_feed.py).

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

**With an AI agent (Claude, ChatGPT, etc.):** paste this repo's link and ask it to set up the system for you — e.g. *"Set up the indian-day-trade-skill repo for paper trading RELIANCE on NSE."* The [SKILL.md](SKILL.md) gives the agent everything it needs: architecture, feed setup, strategy rules, and risk parameters.

**Manual:**

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

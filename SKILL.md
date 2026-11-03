# Indian Day Trade Skill

Production-grade paper-trading infrastructure for NSE (National Stock Exchange of India) day trading. Systematic Opening Range Breakout (ORB) with dual-feed market data, crash-safe execution, validation gates, and per-lane risk management.

**This is engineering infrastructure, not a profitable strategy.** It shows how to build reliable trading systems: feed failover under throttling, exact-restart recovery, backtest validation gates, and a paper ledger. Most open-source trading tools are US-focused; this is built for India's market structure from the ground up.

## How to use this skill

You are an AI agent helping a user set up or run paper trading on NSE. Follow these steps:

1. **Read `docs/architecture.md` first** — it explains the full pipeline (sources → discovery → validation → execution → settlement) so you understand how components connect.
2. **Set up the feed** — ask the user for their Upstox Analytics Token (free, see `docs/setup.md`), or fall back to Yahoo for historical-only work. Never ask for broker login credentials.
3. **Start with `examples/basic_orb.py`** — run it to verify the feed works before building anything custom.
4. **Use the modules, don't rewrite them** — import from `feed/`, `engine/`, `discovery/`, `data/` rather than reimplementing. The edge cases (Cloudflare UA, 5-min aggregation, fail-closed gate) are already handled.
5. **Paper only** — this skill has no broker integration by design. If the user asks about live trading, explain the paper phase comes first and do not wire up order placement.

## Key constraints to respect

- **NSE session:** 09:15–15:30 IST. Nothing trades outside this window.
- **Risk defaults:** 1% per trade, 3 trades/day max, 1 open position, flat by 15:20 IST. Tighten, never loosen, without the user's explicit instruction.
- **Fail-closed:** if market data is unavailable, do not trade. Report the outage, don't guess prices.
- **No credentials in code:** tokens go in environment variables, never in files.

## Repository structure

```
├── feed/               # Market data
│   ├── upstox_feed.py  # Upstox primary (1m → 5m aggregation)
│   ├── yahoo_feed.py   # Yahoo fallback + historical
│   └── router.py       # Dual-feed router
├── engine/             # Execution
│   ├── ledger.py       # Paper P&L with risk management
│   └── timemachine.py  # Backtest validation gate (10k replays)
├── discovery/          # Idea generation
│   ├── scanner.py      # Universe → ORB candidates (5 setups)
│   ├── sentiment.py    # English + Hinglish lexicon scorers
│   └── crowd.py        # Telegram + Google Trends signals
├── data/               # Reference data
│   ├── nse_official.py # Bhavcopy settlement referee
│   └── results_calendar.py  # Earnings blocklist
├── docs/
│   ├── architecture.md # Full infrastructure explained
│   └── setup.md        # Upstox token setup
└── examples/
    └── basic_orb.py    # Minimal runnable ORB
```

See `docs/architecture.md` for the complete system explanation with data-flow diagrams.

## NSE market structure

- **Session:** 09:15–15:30 IST, Monday–Friday
- **Opening range:** 09:15–09:30 (first three 5-minute bars)
- **Entry window:** 09:35–14:30. Flat by 15:20.
- **Instruments:** `NSE_EQ|<ISIN>` format via the instrument master

## Data feeds

**Upstox (primary):** Analytics Token (read-only, 1-year, free). 1-minute candles aggregated to 5-minute bars on the 09:15 grid. Browser User-Agent required (Cloudflare). 50/sec, 500/min limits.

**Yahoo (fallback):** No auth, `*.NS` symbols. Throttles under sustained volume — hence fallback role. Used for historical backfill.

## Strategy

Opening Range Breakout: trigger on first 5-min close above OR high, stop at OR midpoint, 2R target. Every setup passes a 10,000-replay backtest gate before entry; the gate fails closed (abstain on data failure). Catalyst notes can override at reduced risk.

## Risk

1% per trade (0.5% after 3 consecutive losses), 3 trades/day max, 1 open position, flat by 15:20. Paper ledger only — no broker integration.

## Quick start

```bash
export UPSTOX_TOKEN="your-token"  # never commit
python examples/basic_orb.py RELIANCE
```

## Disclaimer

Educational infrastructure. Not financial advice. Paper-trade before considering live capital.

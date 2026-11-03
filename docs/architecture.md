# Architecture — Full Infrastructure

This document explains the complete system: how data flows from market sources through discovery, validation, execution, and settlement.

## System overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   SOURCES   │────▶│  DISCOVERY   │────▶│  VALIDATION │
│             │     │              │     │             │
│ • Upstox    │     │ • Scanner    │     │ • Timemachine│
│ • Yahoo     │     │ • Heroes     │     │   gate      │
│ • NSE/Bhav  │     │ • Sentiment  │     │ • Catalyst  │
│ • News      │     │ • Crowd      │     │   override  │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   EXECUTION  │────▶│  SETTLEMENT │
                    │              │     │             │
                    │ • ORB engine │     │ • Paper     │
                    │ • Risk mgmt  │     │   ledger    │
                    │ • Dual feed  │     │ • Shadow    │
                    └──────────────┘     │   tracking  │
                                         └─────────────┘
```

## 1. Sources (`feed/`)

**Upstox** (`upstox_feed.py`) — Primary live feed.
- Analytics Token (read-only, 1-year, free)
- 1-minute intraday candles → aggregated to 5-minute bars
- Browser User-Agent required (Cloudflare WAF)
- Rate limits: 50/sec, 500/min

**Yahoo Finance** (`yahoo_feed.py`) — Fallback + historical.
- No auth. `*.NS` symbols.
- Known throttling under sustained volume — hence the fallback role.

**Router** (`router.py`) — Tries Upstox for live bars, falls back to Yahoo. Historical ranges go direct to Yahoo.

## 2. Discovery (`discovery/`)

**Scanner** (`scanner.py`) — Narrows the NSE universe (~1,000 liquid names) to ORB candidates.
- Price ₹50–₹5,000, volume 1M+, no circuit locks
- Five setup variants: breakout, retest, tight OR, wide OR, gap breakout

**Heroes** (`heroes.py`) — Catalyst-driven watchlist.
- Scores names on filed catalysts, promoter activity, news clusters, crowd spikes
- Top scorers get dedicated tracking

**Sentiment** (`sentiment.py`) — Dual lexicon scorer.
- English financial lexicon + Hinglish code-mixed lexicon
- Returns separate scores, never blended

**Crowd** (`crowd.py`) — Social signals.
- Telegram channel momentum, Google Trends spikes
- One shared award across sources (no double-counting)

## 3. Validation (`engine/timemachine.py`)

**Backtest gate** — Before any live entry, replay the setup 10,000 times on 60 days of 5-minute history.
- Pass: target-first rate beats breakeven (33.3% for 2R) AND average R ≥ 0
- Fail: skip the trade, log as shadow
- **Fail-closed:** if history is unavailable, abstain (veto) rather than crash

**Catalyst override** — A pre-market catalyst note can override a gate veto at reduced risk (0.5%).

## 4. Execution (`engine/`)

**ORB engine** — The live trading loop.
- Opening range: 09:15–09:30 (first three 5-min bars)
- Trigger: first bar closing above OR high (09:35–14:30)
- Stop: OR midpoint. Target: 2R.
- Polls every 60s (30s in position, 25s near trigger)

**Ledger** (`ledger.py`) — Paper P&L without broker.
- Per-trade risk: 1% (0.5% after 3 consecutive losses)
- Daily cap: 3 trades, soft loss limit
- Max 1 open position

**Reliability guards:**
- **Exact restart:** persist state every cycle; on crash, resume without duplicates
- **Stale-bar suppression:** triggers only on today's bars
- **Feed failover:** Upstox → Yahoo → graceful error

## 5. Settlement (`data/`)

**NSE official** (`nse_official.py`) — Bhavcopy end-of-day closes as the price of record.
- Stale positions settle at the official close
- P&L reconciliation

**Results calendar** (`results_calendar.py`) — Earnings blocklist.
- No entries on results day or day before (binary event risk)

**Shadow tracking** — Gate-vetoed setups are paper-tracked to their outcome, building expectancy data on what the gate blocks.

## Data flow (typical day)

1. **08:15** — Prep: scanner narrows universe, heroes scored, results blocklist built
2. **09:05** — Launch: smoke-test feed, verify ledger, start loop
3. **09:15–09:30** — OR established from live bars
4. **09:35–14:30** — Triggers evaluated; gate validates; entries at 1% risk
5. **15:20** — Flat all positions
6. **15:45** — EOD report: trades, P&L, shadows, reconciliation

## Why this architecture

- **India-specific:** NSE timings, IST timezone, Hinglish sentiment, Upstox feed — not a US system ported over
- **Defensive:** every external dependency has a fallback; every failure mode fails closed or gracefully
- **Auditable:** paper ledger with full event log; shadows track what was skipped and why
- **Paper-first:** no broker integration means no real-money risk during development

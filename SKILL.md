# Indian Day Trade Skill

Production-grade paper-trading infrastructure for NSE (National Stock Exchange of India) day trading. Built for systematic Opening Range Breakout (ORB) strategies with dual-feed market data, crash-safe execution, and per-lane risk management.

This is **engineering infrastructure**, not a profitable strategy. It demonstrates how to build reliable trading systems: feed failover under throttling, exact-restart recovery, validation gates, and a paper ledger. Most open-source trading tools are US-focused; this is built for India's market structure.

## What this covers

- NSE market structure: session timings (09:15–15:30 IST), segments, instrument identification
- Dual-feed market data: Upstox (primary) + Yahoo Finance (fallback) with automatic failover
- Opening Range Breakout strategy: 15-min OR, 5-min trigger bars, 2R targets
- Risk framework: per-trade limits, daily loss caps, consecutive-loss dial-down
- Reliability: exact-restart recovery, gate validation, shadow tracking
- Paper ledger: virtual P&L tracking without broker integration

## NSE market structure

**Session:** 09:15–15:30 IST, Monday–Friday (NSE holidays excepted).
**Opening Range (OR):** First 15 minutes (09:15–09:30), bars at 09:15, 09:20, 09:25.
**Trigger window:** 09:35–14:30. Flat by 15:20.
**Segments:** NSE_EQ for equities. Instrument keys format: `NSE_EQ|<ISIN>`.

## Data sources

### Upstox (primary)
- **Auth:** Analytics Token (read-only, 1-year validity, free). No OAuth redirect, no daily login.
- **Market quotes:** `GET /v2/market-quote/quotes?instrument_key=<KEY>` — no static IP needed.
- **Intraday candles:** `GET /v2/historical-candle/intraday/<KEY>/1minute` — 1-min bars, ISO-8601 +05:30 timestamps marking interval start.
- **Important:** Upstox Cloudflare WAF bans Python-urllib's default User-Agent (Error 1010). Send a browser User-Agent on every request.
- **Rate limits:** 50/sec, 500/min, 2000/30min.
- **5-minute aggregation:** Upstox has no native 5m intraday; aggregate five 1m candles (open=first, high=max, low=min, close=last, volume=sum) bucketed from 09:15 IST.

### Yahoo Finance (fallback)
- **Endpoint:** `https://query2.finance.yahoo.com/v8/finance/chart/<SYM>.NS`
- **No auth.** Known limitation: sustained-volume throttling (token-bucket) walls the feed after ~30 min of aggressive polling.
- **Use for:** fallback when Upstox fails; historical ranges (gate backtest, scanner).

### NSE official (referee)
- **Bhavcopy:** End-of-day official closes. Use as the price of record for settlement disputes.
- **Use for:** stale-position settlement, P&L reconciliation.

## Strategy: Opening Range Breakout

**Setup:**
1. Compute OR from 09:15–09:30 (high/low of first three 5-min bars).
2. Trigger: first 5-min bar closing above OR high (09:35–14:30 only).
3. Stop: OR midpoint. Target: 2R (twice the risk).
4. Position size: risk 1% of lane capital (0.5% after 3 consecutive losses).

**Validation gate (timemachine):**
Before entry, backtest the setup on 60 days of 5-min history (10,000 replays). Skip if the setup leans stop-first or has negative average R. The gate must fail closed — if history is unavailable, abstain (veto) rather than crash.

**Catalyst override:**
A pre-market catalyst note (filed ≤24h or promoter/insider buy ≤7d) can override a gate veto at reduced risk (0.5%).

## Risk framework

| Parameter | Value |
|-----------|-------|
| Per-trade risk | 1% of lane capital (0.5% after 3 consecutive losses) |
| Daily loss soft cap | 3% (Lane A), 1.5% (Lane B) |
| Max trades/day | 3 per lane |
| Max open positions | 1 per lane |
| Same-symbol cross-lane | Refused |
| Flat by | 15:20 IST |

## Reliability patterns

**Exact restart:** Persist per-symbol adjudication state every poll cycle. On restart, restore and skip processed bars — no duplicate entries, no stale exits.

**Feed failover:** Primary (Upstox) → fallback (Yahoo) → graceful error. Never crash on feed failure.

**Gate fail-closed:** If validation history is unavailable, the gate abstains (veto) instead of raising.

**Stale-bar suppression:** Triggers fire only on the current trading day's bars. Prior-session fallback bars may build the OR but never trigger entries.

**Shadow tracking:** Log gate-vetoed setups as paper positions to build expectancy data on what the gate blocks.

## Paper ledger

Track virtual P&L without broker integration:
- Per-lane capital pools (e.g., ₹50,000 each)
- Open positions with entry/stop/target
- Closed trades with R-multiples
- Consecutive-loss counters for risk dial-down
- Day rollover resets counters

## Files in this repo

- `src/upstox_feed.py` — Upstox feed adapter (1m → 5m aggregation)
- `src/feed.py` — Dual-feed router (Upstox primary, Yahoo fallback)
- `src/ledger.py` — Paper ledger with per-lane risk
- `src/engine.py` — ORB engine (OR, trigger, gate, adjudication)
- `docs/architecture.md` — System design
- `docs/setup.md` — Upstox token setup guide
- `examples/basic_orb.py` — Minimal ORB example

## Setup

1. Open an Upstox demat account (free).
2. Generate an Analytics Token: Developer Apps → Analytics tab → Generate Token.
3. Set `UPSTOX_TOKEN` environment variable (never commit it).
4. Install: `pip install -r requirements.txt`
5. Run: `python examples/basic_orb.py`

## Disclaimer

This is educational infrastructure for paper trading. It is not financial advice. The example strategy has not demonstrated profitability. Always paper-trade before considering live capital.

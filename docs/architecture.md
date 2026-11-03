# Architecture — Full Infrastructure

This document is the technical reference for the system: component interfaces, data flow, failure modes, state management, and the design decisions behind each choice. For a quick overview, see the [README](../README.md). For agent usage, see [SKILL.md](../SKILL.md).

## Table of contents

1. [System overview](#1-system-overview)
2. [Feed layer](#2-feed-layer-feed) — market data
3. [Discovery layer](#3-discovery-layer-discovery) — idea generation
4. [Validation layer](#4-validation-layer-enginetimemachinepy) — the backtest gate
5. [Execution layer](#5-execution-layer-engine) — the live loop
6. [Settlement layer](#6-settlement-layer-data) — official records
7. [State management](#7-state-management)
8. [Failure modes & recovery](#8-failure-modes--recovery)
9. [Timing & latency](#9-timing--latency)
10. [Design decisions](#10-design-decisions)

---

## 1. System overview

```
                         ┌─────────────────────────────────┐
                         │         FEED LAYER (feed/)        │
                         │  ┌──────────┐    ┌──────────┐   │
                         │  │ Upstox   │───▶│ Router   │   │
                         │  │ (primary)│    │          │   │
                         │  └──────────┘    │          │   │
                         │  ┌──────────┐    │          │   │
                         │  │ Yahoo    │───▶│          │   │
                         │  │(fallback)│    └────┬─────┘   │
                         │  └──────────┘         │         │
                         └───────────────────────┼─────────┘
                                                 │ 5-min bars
                    ┌────────────────────────────┼─────────────────────────┐
                    │                            ▼                         │
                    │              DISCOVERY LAYER (discovery/)            │
                    │  ┌────────┐  ┌────────┐  ┌───────────┐  ┌────────┐  │
                    │  │Scanner │  │ Heroes │  │ Sentiment │  │ Crowd  │  │
                    │  │        │  │        │  │ EN+Hinglish│  │ TG+Trends│ │
                    │  └───┬────┘  └───┬────┘  └─────┬─────┘  └───┬────┘  │
                    │      └──────┬────┴──────┬──────┘            │       │
                    │             ▼           ▼                   │       │
                    │      ┌────────────────────────────────┐     │       │
                    │      │   Watchlist (ranked candidates) │◀────┘       │
                    │      └───────────────┬────────────────┘             │
                    └──────────────────────┼──────────────────────────────┘
                                           │ candidate + context
                                           ▼
                              ┌────────────────────────┐
                              │ VALIDATION (timemachine)│
                              │  10,000 replays on     │
                              │  60d of 5-min history  │
                              │  ┌──────────────────┐  │
                              │  │ PASS → enter     │  │
                              │  │ FAIL → shadow    │  │
                              │  │ NO DATA → veto   │  │
                              │  └──────────────────┘  │
                              └───────────┬────────────┘
                                          │ validated setup
                                          ▼
                    ┌─────────────────────────────────────────┐
                    │        EXECUTION (engine/)                │
                    │  ┌──────────┐  ┌──────────────────┐     │
                    │  │ ORB loop │─▶│ Ledger           │     │
                    │  │ 60s poll │  │ paper P&L, risk  │     │
                    │  └──────────┘  └──────────────────┘     │
                    │  ┌──────────────────────────────────┐   │
                    │  │ Guards: exact restart, stale-bar │   │
                    │  │ suppression, feed failover       │   │
                    │  └──────────────────────────────────┘   │
                    └───────────────────┬─────────────────────┘
                                        │ fills, events
                                        ▼
                              ┌─────────────────────┐
                              │ SETTLEMENT (data/)  │
                              │ Bhavcopy referee    │
                              │ Results blocklist   │
                              └─────────────────────┘
```

**Data flow direction:** strictly top-down. Discovery never calls execution. Validation never touches the ledger. Each layer exposes a narrow interface to the one below it.

---

## 2. Feed layer (`feed/`)

### 2.1 `upstox_feed.py` — primary live feed

**Interface:**
```python
get_5min_bars(symbol: str) -> list[dict]
# Each dict: {dt, open, high, low, close, volume}
# dt is timezone-aware (Asia/Kolkata)
```

**How it works:**
1. Resolve symbol → Upstox instrument key via the NSE master file (`NSE.json.gz`, cached 24h locally). Format: `NSE_EQ|INE...`.
2. Fetch 1-minute intraday candles from `/v2/historical-candle/intraday/{key}/1minute`.
3. Aggregate to 5-minute buckets aligned to the 09:15 IST session grid.
4. Return chronological bars.

**Critical implementation details:**
- **Browser User-Agent required.** Upstox's Cloudflare WAF returns HTTP 403 (Error 1010) for Python's default `urllib` UA. Every request carries a Chrome UA string.
- **No redirects followed.** A custom `NoRedirect` handler raises on 302 — a redirect from the API is a signal something is wrong, not something to follow silently.
- **Timestamps are interval starts.** Upstox marks each 1-min candle with its start time (09:15:00 = the 09:15–09:16 candle). This matches the engine's bar convention.
- **Newest-first from API, sorted to chronological** before aggregation.

**Rate limits:** 50/sec, 500/min, 2000/30min. Polling ~90 symbols every 60s uses ~1.5 req/sec — comfortable headroom.

### 2.2 `yahoo_feed.py` — fallback + historical

**Interface:**
```python
get_bars(symbol: str, range_: str = "1d", interval: str = "5m") -> tuple[meta, bars]
```

**How it works:** Hits `query2` → `query1` (failover between Yahoo hosts), parses the chart JSON, returns IST-aware bars.

**Known limitation — token-bucket throttling:** Yahoo rate-limits by sustained volume, not just burst. After ~30 minutes of aggressive polling (~50 req/min), the feed walls with 429s for an extended period. This is why Yahoo is the *fallback* for live bars, not the primary. It's the *primary* for historical ranges (60d/5m for the backtest gate, 6mo/1d for context) where request volume is low.

### 2.3 `router.py` — dual-feed router

**Interface:**
```python
get_bars(symbol, range_="1d", interval="5m") -> tuple[meta, bars]
# meta["source"] is "upstox" or "yahoo"
```

**Routing logic:**
- Live intraday (`1d`/`5m`): try Upstox → on any exception, fall back to Yahoo → on failure, raise.
- Historical ranges: Yahoo directly (no point burning Upstox quota).

The router is the *only* thing the engine calls for market data. Swapping feeds or adding a third source means changing one file.

---

## 3. Discovery layer (`discovery/`)

Discovery narrows the universe. It never triggers trades — it produces a ranked watchlist that the validation layer evaluates.

### 3.1 `scanner.py` — universe filter

**Pipeline:**
```
~1,000 liquid NSE names
  → price filter (₹50–₹5,000)
  → volume filter (1M+ shares)
  → circuit-lock check (0 locks in 20 sessions)
  → setup classification (5 variants)
  → ranked candidates
```

**The 5 setup variants:**
| Setup | Description |
|-------|-------------|
| `breakout` | Clean break above OR high on expanding volume |
| `retest` | Breaks OR high, pulls back to retest it, resumes |
| `tight_or` | OR range <1% — compression, expansion expected |
| `wide_or` | OR range >3% — momentum continuation |
| `gap_breakout` | Gaps up pre-market, then breaks OR high |

**Why these filters:** sub-₹50 stocks are too volatile for ORB stops; above ₹5,000 the lot sizing breaks the 1% risk rule on small accounts. The 1M volume gate ensures the stop can actually fill.

### 3.2 `heroes.py` — catalyst scoring

**Rubric** (score ≥ 4 = hero, max 5/day):
| Signal | Points |
|--------|--------|
| Filed catalyst ≤ 24h | +3 |
| Promoter/insider BUY ≤ 7d | +3 |
| News cluster ≥ 5 articles/24h | +2 |
| Crowd spike (shared, never stacks) | +2 |
| Credible bulk/block buy | +1 |
| Euphoria (overbought + hype) | −2 |
| Filed negative (downgrade, fraud, regulatory) | −3 |

**Hard exclusions** (never a hero regardless of score): circuit lock, illiquid, results today/tomorrow.

**Design note:** the rubric is additive and transparent — every point is traceable to a specific signal. No ML black box. When a hero trade fails, you can point at exactly which signal misled you.

### 3.3 `sentiment.py` — dual lexicon

Two scorers, **never blended**:
- **English:** financial lexicon (Loughran-McDonald style) — surge/rally/upgrade vs crash/downgrade/miss.
- **Hinglish:** Hindi-English code-mixed lexicon — the language Indian retail actually uses on Telegram and Twitter (badha/munafa/tej vs gira/nuksaan/mandi).

**Why separate:** English financial news and Hinglish retail chatter are different populations saying different things. Blending them destroys the signal. Each returns −1.0 to +1.0 independently.

### 3.4 `crowd.py` — social signals

- **Telegram momentum:** mentions/hour vs 7-day baseline per channel. 3×+ = spike.
- **Google Trends:** 0–100 interest vs baseline. 3×+ = spike.
- **One shared award:** a spike in *either* source counts once. This prevents double-counting the same news event appearing on both.

---

## 4. Validation layer (`engine/timemachine.py`)

The backtest gate is the system's immune system. No setup reaches the live loop without passing it.

### 4.1 `replay(plan, bars, n=10000, seed=19)`

Simulates the ORB plan against historical 5-minute bars:
- For each historical session, find where the setup would have triggered.
- Walk forward: **stop-first on both-touch** (conservative — if a bar touches both stop and target, count it as a stop).
- Record outcome as +2.0R (target) or −1.0R (stop).

### 4.2 `gate_verdict(counts)`

**Pass criteria (both required):**
1. Target-first rate > breakeven (33.3% for a 2R target) with no significant stop-lean (within 5pp).
2. Average R ≥ 0 across all fires.

**Fail-closed:** zero historical fires → abstain (veto), not crash. A gate that can't evaluate is a gate that says no.

### 4.3 Catalyst override

A pre-market catalyst note (filed ≤ 24h, or promoter buy ≤ 7d) can override a gate veto — but at **0.5% risk** instead of 1%. The reasoning: catalysts change the distribution the backtest measured, but you're still trading against the gate's judgement, so size down.

**Shadow tracking:** vetoed setups are paper-tracked to their actual outcome. Over time this builds expectancy data on *what the gate blocks* — the most valuable dataset in the system for improving the gate itself.

---

## 5. Execution layer (`engine/`)

### 5.1 The ORB loop

```
09:15–09:30  Establish OR from first 3 completed 5-min bars
             OR_high = max(highs), OR_low = min(lows)

09:35–14:30  For each completed bar:
               IF bar closes above OR_high AND no position open:
                 → run backtest gate
                 → IF pass: enter at close, stop = OR midpoint, target = 2R
                 → IF fail: log shadow, skip
               IF position open:
                 → check stop/target on each bar (stop-first on both-touch)
                 → exit and record

15:20        Force-flat any open position (market order at last price)
```

**Polling cadence:** 60s idle, 30s in position, 25s when price is within 0.3% of trigger (near-trigger band). Only *completed* bars are evaluated — never the forming bar.

### 5.2 `ledger.py` — paper ledger

**Position sizing:**
```
risk_amount = capital × risk_pct / 100    # 1%, or 0.5% after 3 consecutive losses
shares = floor(risk_amount / (entry − stop))
```

**Guards:**
- Max 1 open position (slot refusal on second trigger).
- Max 3 trades/day.
- Same-symbol cross-lane refusal (if running multiple lanes).
- Day counters reset on date change (lazy rollover on first entry of the new day).

**P&L:** `pnl = (exit − entry) × shares`, `R = pnl / max_loss`. All values rounded to 2dp (paise).

### 5.3 Reliability guards

| Guard | Problem it solves |
|-------|-------------------|
| **Exact restart** | VM crash mid-session → persist full adjudication state every cycle; on restart, skip already-processed bars, never re-enter, never double-count |
| **Stale-bar suppression** | Feed fallback returns yesterday's bars → triggers only evaluate on bars dated today |
| **Feed failover** | Upstox down → Yahoo → graceful error (never trade blind) |
| **Already-traded guard** | Restart after a close → seed traded-today from the ledger, block re-entry |

---

## 6. Settlement layer (`data/`)

### 6.1 `nse_official.py` — Bhavcopy referee

The Bhavcopy (published ~18:00 IST) is the exchange's official end-of-day record. Any position still open at 15:20 force-flat settles at the Bhavcopy close — not the last traded price seen by the feed. This is the **price of record** for P&L.

### 6.2 `results_calendar.py` — earnings blocklist

No new entries on results day or the day before. Earnings are binary events that break ORB expectancy — the ORB edge comes from intraday order flow, not overnight gaps on news.

---

## 7. State management

**Ephemeral (per-cycle):** bar buffers, trigger proximity, poll timing. Rebuilt from the feed on restart.

**Durable (survives restart):**
- `ledger`: capital, open position, closed trades, consecutive losses, day counters.
- `engine_state`: per-symbol OR levels, processed bar indices, shadow positions.
- `feed_health`: last successful fetch timestamp per feed (drives failover).

**Principle:** anything the loop needs to avoid repeating work after a crash is persisted *every cycle*, atomically (write temp + rename). The cost is negligible; the alternative is duplicate entries.

---

## 8. Failure modes & recovery

| Failure | Detection | Response |
|---------|-----------|----------|
| Upstox 429/403 | HTTP status on fetch | Router falls back to Yahoo |
| Both feeds down | Consecutive fetch failures | Loop pauses, alerts, **does not trade** |
| VM crash / replacement | Process gone on next poll | External guard restarts; exact-restart resumes |
| Gate history unavailable | Exception in `replay()` | Fail-closed: veto the setup |
| Stale bars from fallback | `bar.dt.date() != today` | Suppress triggers, keep OR from live bars only |
| Position open at 15:20 | Clock check each cycle | Force-flat at last price |
| Token expired (Upstox) | 401 on API call | Alert for manual rotation; Yahoo covers live bars |

**What the system never does:** trade on stale data, double-enter after restart, exceed risk limits, or silently skip a failure.

---

## 9. Timing & latency

| Operation | Typical latency |
|-----------|-----------------|
| Upstox 1-min fetch (1 symbol) | ~0.5s |
| Full 90-symbol poll cycle | ~45s (sequential; parallel is future work) |
| Yahoo fallback fetch | 1–3s per symbol |
| Backtest gate (10k replays) | 2–5s per setup |
| State persist (per cycle) | <10ms |

The 60s poll interval is the binding constraint: a full Upstox cycle fits inside it, but barely. If the universe grows past ~120 symbols, parallel fetching becomes necessary.

---

## 10. Design decisions

**Paper-first, no broker integration.** The paper phase validates the *system* (feeds, gates, risk, recovery) before capital is at risk. Wiring up order placement is a separate, deliberate decision — not something that happens by accident.

**Fail-closed everywhere.** Every validation, every feed, every gate: when in doubt, don't trade. A missed opportunity costs nothing in paper trading; a bad fill corrupts the experiment.

**India-specific, not ported.** NSE session times, IST timezone handling, Hinglish sentiment, Upstox feed quirks, Bhavcopy settlement, ₹-denominated risk — these aren't adaptations of a US system, they're the starting point.

**Transparent over clever.** Additive hero rubric, lexicon sentiment, rule-based ORB. Every decision is auditable. When something fails, you know *which rule* failed — which is how the system improves.

**Boring reliability.** Atomic state writes, idempotent restarts, lazy day rollover, no clever caching. The most important code in the system is the least interesting.

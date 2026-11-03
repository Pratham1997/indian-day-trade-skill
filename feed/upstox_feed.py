#!/usr/bin/env python3
"""Upstox feed adapter — 1-minute intraday candles aggregated to 5-minute bars.

Uses the Upstox Analytics Token (read-only, free). Set UPSTOX_TOKEN env var.
IMPORTANT: Upstox Cloudflare WAF bans Python-urllib's default User-Agent.
A browser User-Agent is REQUIRED on every request.
"""

import gzip
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      " (KHTML, like Gecko) Chrome/131.0 Safari/537.36")
API_HOST = "api.upstox.com"
MASTER_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
CACHE_DIR = Path(os.environ.get("UPSTOX_CACHE_DIR", ".upstox_cache"))
MASTER_CACHE = CACHE_DIR / "instruments.json"
MASTER_TTL = 24 * 3600
SESSION_START = (9, 15)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused")


def _token():
    tok = os.environ.get("UPSTOX_TOKEN")
    if not tok:
        raise RuntimeError("UPSTOX_TOKEN env var not set")
    return tok


def _api_get(path, timeout=30):
    req = urllib.request.Request(
        f"https://{API_HOST}{path}",
        headers={"Accept": "application/json",
                 "User-Agent": UA,
                 "Authorization": f"Bearer {_token()}"},
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {}
        return e.code, body


def _refresh_master():
    req = urllib.request.Request(MASTER_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        items = json.loads(gzip.decompress(r.read()))
    mapping = {it["trading_symbol"]: it["instrument_key"]
               for it in items
               if it.get("segment") == "NSE_EQ" and it.get("instrument_type") == "EQ"
               and it.get("trading_symbol") and it.get("instrument_key")}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_CACHE.write_text(json.dumps(mapping))
    return mapping


def symbol_to_key(symbol):
    sym = symbol.upper().removesuffix(".NS")
    if MASTER_CACHE.exists() and time.time() - MASTER_CACHE.stat().st_mtime < MASTER_TTL:
        mapping = json.loads(MASTER_CACHE.read_text())
    else:
        mapping = _refresh_master()
    key = mapping.get(sym)
    if not key:
        raise RuntimeError(f"no Upstox instrument key for {symbol}")
    return key


def get_5min_bars(symbol):
    """Returns 5-min bars: list of dicts with dt, open, high, low, close, volume."""
    key = symbol_to_key(symbol).replace("|", "%7C")
    status, body = _api_get(f"/v2/historical-candle/intraday/{key}/1minute")
    if status != 200:
        raise RuntimeError(f"upstox intraday failed for {symbol}: HTTP {status}")
    candles = []
    for c in body.get("data", {}).get("candles", []):
        dt = datetime.fromisoformat(c[0])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        candles.append((dt, c[1], c[2], c[3], c[4], c[5] or 0))
    candles.sort(key=lambda x: x[0])
    # Aggregate to 5-min buckets from 09:15 IST
    buckets = {}
    for dt, o, h, l, c, v in candles:
        day_start = datetime(dt.year, dt.month, dt.day, *SESSION_START, tzinfo=IST)
        mins = int((dt - day_start).total_seconds() // 60)
        if mins < 0:
            continue
        idx = mins // 5
        b = buckets.setdefault(idx, {"dt": day_start + timedelta(minutes=idx * 5),
                                     "open": o, "high": h, "low": l,
                                     "close": c, "volume": 0})
        b["high"] = max(b["high"], h)
        b["low"] = min(b["low"], l)
        b["close"] = c
        b["volume"] += v
    return [buckets[i] for i in sorted(buckets)]

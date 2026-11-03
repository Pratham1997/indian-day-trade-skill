#!/usr/bin/env python3
"""Yahoo Finance feed — fallback source for NSE equities.

No auth required. Known limitation: sustained-volume throttling
(token-bucket) can wall the feed after ~30 min of aggressive polling.
Use as fallback behind Upstox, or for historical ranges.
"""

import gzip
import json
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
      " (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def get_bars(symbol, range_="1d", interval="5m"):
    """Returns (meta, bars). Bars: dt (aware IST), open/high/low/close/volume."""
    if not symbol.upper().endswith(".NS"):
        symbol = symbol.upper() + ".NS"
    last_err = None
    for host in ("query2", "query1"):
        try:
            req = urllib.request.Request(
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}"
                f"?range={range_}&interval={interval}",
                headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                data = json.loads(raw)
            result = data["chart"]["result"][0]
            break
        except Exception as e:
            last_err = e
    else:
        raise RuntimeError(f"yahoo chart failed for {symbol}: {last_err}")

    quote = result["indicators"]["quote"][0]
    bars = []
    for i, ts in enumerate(result.get("timestamp", [])):
        if quote["close"][i] is None or quote["open"][i] is None:
            continue
        bars.append({
            "dt": datetime.fromtimestamp(ts, IST),
            "open": quote["open"][i], "high": quote["high"][i],
            "low": quote["low"][i], "close": quote["close"][i],
            "volume": quote["volume"][i] or 0,
        })
    return {"source": "yahoo", "symbol": symbol}, bars

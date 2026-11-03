# Setup — Upstox Analytics Token

## 1. Open a Upstox demat account

Free. The Analytics Token is available to account holders at no cost.

## 2. Generate the token

1. Log in to [upstox.com](https://upstox.com)
2. Go to **API / Developer** section
3. Create an app (redirect URI can be a placeholder for token-only use)
4. Generate an **Analytics Token** — read-only, 1-year validity

## 3. Set the environment variable

```bash
export UPSTOX_TOKEN="your-token-here"
```

Never commit this. The `.gitignore` excludes `.env` files — put it there for persistence:

```bash
echo 'export UPSTOX_TOKEN="your-token-here"' >> ~/.env
```

## 4. Verify

```bash
python -c "
import sys; sys.path.insert(0, 'feed')
from upstox_feed import get_5min_bars
bars = get_5min_bars('RELIANCE')
print(f'{len(bars)} bars, latest close: {bars[-1][\"close\"]}')
"
```

## Rate limits

- 50 requests/second
- 500 requests/minute
- 2000 requests/30 minutes

Polling ~90 symbols every 60 seconds stays well inside these.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 403 / Error 1010 | Cloudflare blocking non-browser UA | The adapter already sends a browser UA — check you're using `feed/upstox_feed.py` |
| 401 | Token expired or invalid | Regenerate in the Upstox dashboard |
| Empty candles | Market closed (weekend/holiday) | Check [NSE holidays](https://www.nseindia.com/trade/market-holidays) |

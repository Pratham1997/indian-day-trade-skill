#!/usr/bin/env python3
"""NSE official data — Bhavcopy end-of-day settlement referee.

The Bhavcopy (published ~18:00 IST daily) is the official record of
closing prices. Stale positions settle at the Bhavcopy close;
the paper ledger reconciles against it.

Download: https://www.nseindia.com/all-reports
"""


def bhavcopy_url(date_str):
    """Bhavcopy download URL for YYYY-MM-DD."""
    # Format: cmDDMMMYYYYbhav.csv.zip, e.g. cm03NOV2026bhav.csv.zip
    from datetime import datetime
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    stamp = dt.strftime("%d%b%Y").upper()
    return (f"https://www.nseindia.com/content/historical/EQUITIES/"
            f"{dt.year}/{dt.strftime('%b').upper()}/cm{stamp}bhav.csv.zip")


def settle_at_close(symbol, bhavcopy_close):
    """Returns the official settlement price for a stale position."""
    return bhavcopy_close

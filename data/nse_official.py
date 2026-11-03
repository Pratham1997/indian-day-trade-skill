#!/usr/bin/env python3
"""NSE official data — official EOD closing prices as the price of record.

NSE publishes official closing prices ~18:00 IST daily (the "Bhavcopy" file).
Any position still open at the 15:20 force-flat settles at the official
close — not the last traded price seen by the feed. The paper ledger
reconciles against these.

Download: https://www.nseindia.com/all-reports
"""


def official_close_url(date_str):
    """Official EOD file download URL for YYYY-MM-DD."""
    # Format: cmDDMMMYYYYbhav.csv.zip, e.g. cm03NOV2026bhav.csv.zip
    from datetime import datetime
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    stamp = dt.strftime("%d%b%Y").upper()
    return (f"https://www.nseindia.com/content/historical/EQUITIES/"
            f"{dt.year}/{dt.strftime('%b').upper()}/cm{stamp}bhav.csv.zip")


def settle_at_close(symbol, official_close):
    """Returns the official settlement price for a stale position."""
    return official_close

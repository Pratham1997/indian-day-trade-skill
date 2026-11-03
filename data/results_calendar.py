#!/usr/bin/env python3
"""Results calendar — earnings blocklist.

No new entries on a stock's results day or the day before.
Binary event risk breaks ORB expectancy; the calendar keeps
the engine out of those names.

Primary source: NSE board-meeting announcements.
"""


def is_blocked(symbol, date_str, board_meetings):
    """True if symbol has results on date_str or the next trading day.

    board_meetings: dict of symbol -> list of YYYY-MM-DD dates
    """
    from datetime import datetime, timedelta
    dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    dates = board_meetings.get(symbol.upper(), [])
    for d in dates:
        meeting = datetime.strptime(d, "%Y-%m-%d").date()
        if meeting in (dt, dt + timedelta(days=1)):
            return True
    return False

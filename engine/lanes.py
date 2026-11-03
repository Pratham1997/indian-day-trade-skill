#!/usr/bin/env python3
"""Dual-lane execution engine — Track A (systematic) + Track B (hero).

Track A: pure ORB, 1% risk, backtest gate required.
Track B: catalyst-driven hero entries, 0.5% risk, gate recorded not blocking.

Each lane has its own capital pool, risk limits, and position slot.
Same symbol can never be held in both lanes simultaneously.
"""

from .ledger import Ledger
from .timemachine import replay, gate_verdict
from discovery.heroes import score_hero, is_excluded


# Lane configuration
LANE_A = {
    "name": "Track A",
    "capital": 50000.0,
    "risk_pct": 1.0,          # 1% per trade (0.5% after 3 consecutive losses)
    "daily_loss_cap_pct": 3.0, # soft cap: stop new entries beyond this
    "max_trades_day": 3,
    "requires_gate": True,     # backtest gate must pass
}

LANE_B = {
    "name": "Track B",
    "capital": 50000.0,
    "risk_pct": 0.5,          # 0.5% per trade (hero entries are higher-conviction but experimental)
    "daily_loss_cap_pct": 1.5, # tighter cap — hero track is experimental
    "max_trades_day": 3,
    "requires_gate": False,    # gate recorded, not blocking
    "hero_threshold": 4,       # minimum hero score to enter
    "max_heroes_day": 5,       # cap hero entries per day
}


class DualLaneEngine:
    def __init__(self):
        self.lane_a = Ledger(capital=LANE_A["capital"])
        self.lane_b = Ledger(capital=LANE_B["capital"])
        self.heroes_today = 0
        self.shadows = []  # vetoed setups tracked to outcome

    def _cross_lane_symbol(self, symbol):
        """Same symbol can't be held in both lanes."""
        open_symbols = set()
        if self.lane_a.open_position:
            open_symbols.add(self.lane_a.open_position["symbol"])
        if self.lane_b.open_position:
            open_symbols.add(self.lane_b.open_position["symbol"])
        return symbol in open_symbols

    def _daily_loss_hit(self, ledger, cap_pct):
        day_pnl = sum(t["pnl"] for t in ledger.closed_trades
                      if t.get("is_today", True))
        return day_pnl <= -(ledger.capital * cap_pct / 100)

    def try_track_a(self, symbol, entry, stop, target, bars, date_str):
        """Track A: ORB entry, requires backtest gate pass."""
        if self._cross_lane_symbol(symbol):
            return None, "cross-lane symbol refusal"
        if self._daily_loss_hit(self.lane_a, LANE_A["daily_loss_cap_pct"]):
            return None, "Track A daily loss cap hit"

        # Backtest gate
        plan = {"entry": entry, "stop": stop, "target": target}
        counts = replay(plan, bars)
        passed, verdict = gate_verdict(counts)
        if not passed:
            self.shadows.append({"symbol": symbol, "lane": "A",
                                 "reason": f"gate veto: {verdict}",
                                 "plan": plan})
            return None, f"gate veto: {verdict}"

        pos = self.lane_a.open_trade(symbol, entry, stop, target, date_str)
        return pos, f"Track A entry (gate: {verdict[:50]})"

    def try_track_b(self, symbol, entry, stop, target, hero_signals, date_str):
        """Track B: hero entry, gate recorded not blocking."""
        if self._cross_lane_symbol(symbol):
            return None, "cross-lane symbol refusal"
        if self._daily_loss_hit(self.lane_b, LANE_B["daily_loss_cap_pct"]):
            return None, "Track B daily loss cap hit"
        if self.heroes_today >= LANE_B["max_heroes_day"]:
            return None, "hero daily cap reached"
        if is_excluded(symbol, **{k: hero_signals.get(k, False)
                                  for k in ("circuit_lock", "illiquid", "results_soon")}):
            return None, "hero hard exclusion"

        score, is_hero = score_hero(hero_signals)
        if not is_hero:
            return None, f"hero score {score} below threshold {LANE_B['hero_threshold']}"

        # Gate runs but doesn't block — recorded for analysis
        plan = {"entry": entry, "stop": stop, "target": target}
        try:
            counts = replay(plan, [])  # placeholder: real impl passes historical bars
            _, verdict = gate_verdict(counts)
        except Exception:
            verdict = "gate abstained"

        pos = self.lane_b.open_trade(symbol, entry, stop, target, date_str)
        self.heroes_today += 1
        return pos, f"Track B hero entry (score {score}, gate: {verdict[:50]})"

    def new_day(self, date_str):
        self.lane_a.new_day(date_str)
        self.lane_b.new_day(date_str)
        self.heroes_today = 0

    def summary(self):
        return {
            "track_a": self.lane_a.summary(),
            "track_b": self.lane_b.summary(),
            "heroes_today": self.heroes_today,
            "shadows_open": len(self.shadows),
        }

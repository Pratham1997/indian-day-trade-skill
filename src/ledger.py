#!/usr/bin/env python3
"""Simplified paper ledger — virtual P&L tracking without broker integration."""

class Ledger:
    def __init__(self, capital=50000.0):
        self.capital = capital
        self.open_position = None
        self.closed_trades = []
        self.consecutive_losses = 0

    def risk_pct(self):
        # Step down to 0.5% after 3 consecutive losses
        return 0.5 if self.consecutive_losses >= 3 else 1.0

    def open_trade(self, symbol, entry, stop, target):
        if self.open_position:
            raise RuntimeError("a position is already open (max 1)")
        risk = entry - stop
        if risk <= 0:
            raise ValueError("stop must be below entry for a long")
        pct = self.risk_pct()
        max_loss = round(self.capital * pct / 100, 2)
        shares = int(max_loss // risk)
        if shares < 1:
            raise RuntimeError("position too small to trade")
        self.open_position = {
            "symbol": symbol, "entry": entry, "stop": stop, "target": target,
            "shares": shares, "max_loss": round(shares * risk, 2), "risk_pct": pct,
        }
        return self.open_position

    def close_trade(self, exit_price, reason):
        pos = self.open_position
        if not pos:
            raise RuntimeError("no open position")
        pnl = round((exit_price - pos["entry"]) * pos["shares"], 2)
        r = round(pnl / pos["max_loss"], 3) if pos["max_loss"] else 0.0
        trade = {**pos, "exit": exit_price, "reason": reason, "pnl": pnl, "r": r}
        self.capital = round(self.capital + pnl, 2)
        self.closed_trades.append(trade)
        self.consecutive_losses = 0 if pnl > 0 else self.consecutive_losses + 1
        self.open_position = None
        return trade

    def summary(self):
        wins = sum(1 for t in self.closed_trades if t["pnl"] > 0)
        total_r = sum(t["r"] for t in self.closed_trades)
        return {
            "capital": self.capital,
            "closed": len(self.closed_trades),
            "wins": wins,
            "total_pnl": round(sum(t["pnl"] for t in self.closed_trades), 2),
            "avg_r": round(total_r / len(self.closed_trades), 3) if self.closed_trades else 0.0,
        }

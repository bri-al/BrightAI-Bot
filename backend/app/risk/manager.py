from datetime import datetime, timezone
from typing import Optional
from app.config import settings


class TrailingStop:
    def __init__(self, atr_value: float = 0.0):
        self.atr_value = atr_value
        self.entry_price: Optional[float] = None
        self.highest_price: Optional[float] = None
        self.lowest_price: Optional[float] = None
        self.activated = False

    def update(self, current_price: float, direction: str) -> Optional[float]:
        if self.entry_price is None:
            self.entry_price = current_price
        act_dist = self.atr_value * 1.5 if self.atr_value > 0 else self.entry_price * 0.01
        trail_dist = self.atr_value * 1.0 if self.atr_value > 0 else self.entry_price * 0.005
        if direction == "long":
            if not self.activated:
                if self.highest_price is None or current_price > self.highest_price:
                    self.highest_price = current_price
                gain = current_price - self.entry_price
                if gain >= act_dist:
                    self.activated = True
            else:
                if current_price > self.highest_price:
                    self.highest_price = current_price
                trail_level = self.highest_price - trail_dist
                if current_price <= trail_level:
                    return trail_level
        elif direction == "short":
            if not self.activated:
                if self.lowest_price is None or current_price < self.lowest_price:
                    self.lowest_price = current_price
                gain = self.entry_price - current_price
                if gain >= act_dist:
                    self.activated = True
            else:
                if current_price < self.lowest_price:
                    self.lowest_price = current_price
                trail_level = self.lowest_price + trail_dist
                if current_price >= trail_level:
                    return trail_level
        return None


class Position:
    def __init__(self, symbol: str, direction: str, entry_price: float, size: float,
                 stop_loss: float, take_profit: Optional[float], strategy: str,
                 timestamp: Optional[str] = None, atr_value: float = 0.0):
        self.symbol = symbol
        self.direction = direction
        self.entry_price = entry_price
        self.size = size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.strategy = strategy
        self.atr_value = atr_value
        self.trailing_stop = TrailingStop(atr_value=atr_value)
        self.entry_time = timestamp or datetime.now(timezone.utc).isoformat()
        self.current_price = entry_price
        self.unrealized_pnl = 0.0
        self.highest_unrealized = 0.0
        self.lowest_unrealized = 0.0
        self.breakeven_activated = False

    def update_price(self, price: float):
        self.current_price = price
        if self.direction == "long":
            self.unrealized_pnl = (price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.size
        if self.unrealized_pnl > self.highest_unrealized:
            self.highest_unrealized = self.unrealized_pnl
        if self.unrealized_pnl < self.lowest_unrealized:
            self.lowest_unrealized = self.unrealized_pnl

    def check_trailing_stop(self, current_price: float) -> Optional[float]:
        return self.trailing_stop.update(current_price, self.direction)

    def check_breakeven(self, current_price: float) -> bool:
        if self.breakeven_activated:
            return False
        if self.direction == "long":
            favorable_move = current_price - self.entry_price
        else:
            favorable_move = self.entry_price - current_price
        atr_threshold = self.atr_value * 1.5 if self.atr_value > 0 else self.entry_price * 0.02
        if favorable_move >= atr_threshold:
            self.stop_loss = self.entry_price
            self.breakeven_activated = True
            return True
        return False

    def time_held_minutes(self) -> float:
        now = datetime.now(timezone.utc)
        entry = datetime.fromisoformat(self.entry_time)
        return (now - entry).total_seconds() / 60

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "size": self.size,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "strategy": self.strategy,
            "entry_time": self.entry_time,
            "time_held_min": round(self.time_held_minutes(), 1),
        }


class RiskState:
    def __init__(self):
        self.initial_capital = settings.initial_capital
        self.current_equity = settings.initial_capital
        self.peak_equity = settings.initial_capital
        self.open_positions = 0
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.drawdown = 0.0
        self.last_reset_date = ""
        self.trade_history: list[dict] = []
        self.rejected_trades: list[dict] = []
        self.is_trading = False
        self.kill_switch = False
        self.active_positions: dict[str, Position] = {}
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.recently_closed: list[dict] = []

    def reset_daily(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.last_reset_date != today:
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset_date = today

    def update_drawdown(self):
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
        self.drawdown = (self.peak_equity - self.current_equity) / max(self.peak_equity, 1)

    def _check_capital_base(self) -> tuple[bool, str]:
        if self.current_equity <= 0:
            return False, "Account balance is zero or negative"
        if self.drawdown >= settings.max_drawdown:
            return False, f"Max drawdown exceeded ({self.drawdown*100:.1f}%)"
        return True, ""

    def _check_daily_loss(self) -> tuple[bool, str]:
        if self.daily_pnl >= 0:
            return True, ""
        daily_loss_pct = abs(self.daily_pnl) / max(self.current_equity, 1)
        if daily_loss_pct >= settings.max_daily_loss:
            return False, f"Daily loss limit reached ({daily_loss_pct*100:.1f}%)"
        return True, ""

    def _check_open_positions(self) -> tuple[bool, str]:
        if self.open_positions >= settings.max_open_positions:
            return False, f"Max open positions reached ({settings.max_open_positions})"
        return True, ""

    def _check_daily_trades(self) -> tuple[bool, str]:
        if self.daily_trades >= 20:
            return False, "Daily trade limit reached (20)"
        return True, ""

    def _check_consecutive_losses(self) -> tuple[bool, str]:
        if self.consecutive_losses >= 5:
            return False, f"Consecutive loss limit reached ({self.consecutive_losses})"
        return True, ""

    def _check_correlation(self, symbol: str) -> tuple[bool, str]:
        if symbol in self.active_positions:
            return False, f"Already in position for {symbol}"
        correlated_pairs = {
            "EURUSD": ["GBPUSD", "USDCHF"],
            "GBPUSD": ["EURUSD", "USDCHF"],
            "USDCHF": ["EURUSD", "GBPUSD"],
            "BTCUSDT": ["ETHUSDT", "SOLUSDT"],
            "ETHUSDT": ["BTCUSDT", "SOLUSDT"],
            "SOLUSDT": ["BTCUSDT", "ETHUSDT"],
            "XAUUSD": ["XAGUSD"],
            "XAGUSD": ["XAUUSD"],
        }
        correlated_symbols = correlated_pairs.get(symbol, [])
        for pos_sym in self.active_positions:
            if pos_sym in correlated_symbols:
                return False, f"Already in correlated position ({pos_sym})"
        return True, ""

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str,
        volatility_mult: float = 1.0,
        regime: Optional[str] = None,
    ) -> float:
        base_risk = settings.max_risk_per_trade

        if regime == "strong_trend":
            regime_mult = 1.2
        elif regime in ("trend", "range"):
            regime_mult = 1.0
        elif regime == "weak_trend":
            regime_mult = 0.75
        elif regime in ("volatile", "choppy"):
            regime_mult = 0.5
        else:
            regime_mult = 0.8

        if self.consecutive_losses >= 3:
            regime_mult *= 0.5
        elif self.consecutive_wins >= 3:
            regime_mult *= 1.15

        risk_amount = self.current_equity * base_risk * volatility_mult * regime_mult
        if direction == "long":
            risk_per_unit = entry_price - stop_loss
        else:
            risk_per_unit = stop_loss - entry_price
        if risk_per_unit <= 0:
            return 0.0
        size = risk_amount / risk_per_unit

        min_size_by_value = settings.min_position_value / max(entry_price, 0.001)
        if size < min_size_by_value:
            size = min_size_by_value

        max_notional = self.current_equity * 3.0 / max(entry_price, 0.001)
        if size > max_notional:
            size = max_notional

        return size

    def validate_trade(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float],
        direction: str,
        current_open_positions: Optional[int] = None,
        symbol: Optional[str] = None,
    ) -> tuple[bool, str]:
        self.reset_daily()
        self.update_drawdown()

        if current_open_positions is not None:
            self.open_positions = current_open_positions

        checks = [
            self._check_capital_base(),
            self._check_daily_loss(),
            self._check_open_positions(),
            self._check_daily_trades(),
            self._check_consecutive_losses(),
        ]

        if symbol:
            checks.append(self._check_correlation(symbol))

        for passed, msg in checks:
            if not passed:
                return False, msg

        if take_profit is not None:
            if direction == "long":
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            if risk > 0 and reward / risk < settings.min_rr_ratio:
                return False, f"R/R {reward/risk:.2f} below min {settings.min_rr_ratio}"

        if self.kill_switch:
            return False, "Kill switch is active"

        return True, "approved"

    def open_trade(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float],
        size: float,
        strategy: str,
        atr_value: float = 0.0,
    ) -> Position:
        pos = Position(
            symbol=symbol, direction=direction, entry_price=entry_price,
            size=size, stop_loss=stop_loss, take_profit=take_profit, strategy=strategy,
            atr_value=atr_value,
        )
        self.active_positions[symbol] = pos
        self.open_positions = len(self.active_positions)
        return pos

    def close_trade(self, symbol: str, exit_price: float) -> Optional[dict]:
        pos = self.active_positions.pop(symbol, None)
        if pos is None:
            return None
        if pos.direction == "long":
            pnl = (exit_price - pos.entry_price) * pos.size
        else:
            pnl = (pos.entry_price - exit_price) * pos.size
        self.current_equity += pnl
        self.daily_pnl += pnl
        self.daily_trades += 1
        self.open_positions = len(self.active_positions)
        self.update_drawdown()

        if pnl > 0:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "strategy": pos.strategy,
            "direction": pos.direction,
            "entry": pos.entry_price,
            "exit": exit_price,
            "size": pos.size,
            "pnl": round(pnl, 2),
            "equity_after": self.current_equity,
        }
        self.trade_history.append(result)
        self.recently_closed.append(result)
        return result

    def sync_account(self, balance: float, equity: float):
        self.current_equity = equity
        if equity > self.peak_equity:
            self.peak_equity = equity

    def sync_from_broker(self, broker_positions: list[dict]):
        by_symbol: dict[str, list[dict]] = {}
        for bp in broker_positions:
            by_symbol.setdefault(bp["symbol"], []).append(bp)

        synced_symbols = set()
        for sym, positions in by_symbol.items():
            synced_symbols.add(sym)
            net_size = sum(p["size"] * (1 if p["direction"] == "long" else -1) for p in positions)
            if abs(net_size) < 0.0001:
                if sym in self.active_positions:
                    self.active_positions.pop(sym, None)
                continue
            direction = "long" if net_size > 0 else "short"
            abs_size = abs(net_size)
            avg_entry = sum(p["entry"] * p["size"] for p in positions) / sum(p["size"] for p in positions)
            cur = positions[-1]["current"]
            if sym in self.active_positions:
                pos = self.active_positions[sym]
                pos.size = abs_size
                pos.direction = direction
                pos.entry_price = avg_entry
                pos.current_price = cur
            else:
                pos = Position(
                    symbol=sym, direction=direction, entry_price=avg_entry,
                    size=abs_size, stop_loss=0, take_profit=0, strategy="broker",
                )
                pos.current_price = cur
                self.active_positions[sym] = pos

        for sym in list(self.active_positions.keys()):
            if sym not in synced_symbols:
                self.active_positions.pop(sym, None)
        self.open_positions = len(self.active_positions)

    def update_positions(self, market_prices: dict[str, float]):
        for sym, pos in list(self.active_positions.items()):
            if sym in market_prices:
                price = market_prices[sym]
                pos.update_price(price)
                pos.check_breakeven(price)
                trail_stop = pos.check_trailing_stop(price)
                if trail_stop is not None:
                    self.close_trade(sym, trail_stop)

    def to_dict(self) -> dict:
        return {
            "balance": round(self.current_equity, 2),
            "equity": round(self.current_equity, 2),
            "peak_equity": round(self.peak_equity, 2),
            "drawdown": round(self.drawdown * 100, 2),
            "open_positions": len(self.active_positions),
            "daily_trades": self.daily_trades,
            "daily_pnl": round(self.daily_pnl, 2),
            "total_trades": len(self.trade_history),
            "is_trading": self.is_trading,
            "kill_switch": self.kill_switch,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "positions": {sym: pos.to_dict() for sym, pos in self.active_positions.items()},
        }


risk_engine = RiskState()

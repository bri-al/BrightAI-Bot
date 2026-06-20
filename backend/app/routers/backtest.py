import json
import statistics
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.schemas import BacktestRequest, BacktestResponse, BacktestTrade
from app.config import settings
from app.engine.market import market_data
from app.engine.indicators import ema, rsi, macd, bollinger_bands, atr, volatility
from app.engine.signals import _momentum_signal, _mean_reversion_signal, _scalping_signal
from app.auth import verify_api_key

router = APIRouter(prefix="/backtest", tags=["Backtesting"])


@router.post("")
async def run_backtest(body: BacktestRequest, auth: str = Depends(verify_api_key)):
    candles = await market_data.fetch_historical(body.symbol, limit=body.days * 24)
    if len(candles) < 100:
        candles = market_data.generate_synthetic(body.symbol, body.days)

    if len(candles) < 100:
        raise HTTPException(400, "Insufficient data for backtesting")

    result = _run_backtest(candles, body.strategy, body.initial_capital)
    return result


@router.post("/{symbol}/{strategy_name}")
async def backtest_symbol_strategy(
    symbol: str,
    strategy_name: str,
    initial_capital: float = 100000.0,
    days: int = 365,
    auth: str = Depends(verify_api_key),
):
    candles = await market_data.fetch_historical(symbol, limit=days * 24)
    if len(candles) < 100:
        candles = market_data.generate_synthetic(symbol, days)
    if len(candles) < 100:
        raise HTTPException(400, "Insufficient data")

    result = _run_backtest(candles, strategy_name, initial_capital)
    return result


def _run_backtest(candles: list[dict], strategy: str, capital: float) -> BacktestResponse:
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    n = len(closes)

    equity = capital
    peak_equity = capital
    max_dd = 0.0
    trades: list[BacktestTrade] = []
    in_position = False
    position_type = None
    entry_price = 0.0
    entry_idx = 0
    sl_price = 0.0
    tp_price = 0.0
    position_size = 0.0

    atr_cache = atr(highs, lows, closes, 14)

    def _get_atr(idx):
        if idx < len(atr_cache) and atr_cache[idx] is not None:
            return atr_cache[idx]
        return (highs[idx] - lows[idx]) if idx < len(highs) else 0

    for i in range(n):
        if not in_position:
            signal = _generate_signal_for_backtest(closes, highs, lows, i, candles, strategy)
            if signal == "buy":
                entry_price = closes[i]
                position_type = "long"
                in_position = True
                entry_idx = i
                atr_val = _get_atr(i) or closes[i] * 0.02
                sl_price = entry_price - 1.5 * atr_val
                tp_price = entry_price + 3.0 * atr_val
                risk_amount = equity * settings.max_risk_per_trade
                risk_per_unit = entry_price - sl_price
                position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
            elif signal == "sell":
                entry_price = closes[i]
                position_type = "short"
                in_position = True
                entry_idx = i
                atr_val = _get_atr(i) or closes[i] * 0.02
                sl_price = entry_price + 1.5 * atr_val
                tp_price = entry_price - 3.0 * atr_val
                risk_amount = equity * settings.max_risk_per_trade
                risk_per_unit = sl_price - entry_price
                position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        else:
            hit_sl = (position_type == "long" and lows[i] <= sl_price) or \
                     (position_type == "short" and highs[i] >= sl_price)
            hit_tp = (position_type == "long" and highs[i] >= tp_price) or \
                     (position_type == "short" and lows[i] <= tp_price)
            exit_price = None
            if hit_sl:
                exit_price = sl_price
            elif hit_tp:
                exit_price = tp_price

            if exit_price is not None:
                pnl = (exit_price - entry_price) * position_size if position_type == "long" \
                      else (entry_price - exit_price) * position_size
                equity += pnl
                trades.append(BacktestTrade(
                    entry_idx=entry_idx, exit_idx=i,
                    type=position_type, entry=entry_price,
                    exit=exit_price, pnl=round(pnl, 2),
                    pnl_pct=round(pnl / (entry_price * position_size) if position_size > 0 and entry_price > 0 else 0, 4),
                ))
                in_position = False
                if equity > peak_equity:
                    peak_equity = equity
                dd = (peak_equity - equity) / peak_equity
                if dd > max_dd:
                    max_dd = dd

    # Close open position at end
    if in_position:
        exit_price = closes[-1]
        pnl = (exit_price - entry_price) * position_size if position_type == "long" \
              else (entry_price - exit_price) * position_size
        equity += pnl
        trades.append(BacktestTrade(
            entry_idx=entry_idx, exit_idx=n - 1,
            type=position_type, entry=entry_price,
            exit=exit_price, pnl=round(pnl, 2),
            pnl_pct=round(pnl / (entry_price * position_size) if position_size > 0 and entry_price > 0 else 0, 4),
        ))

    num_trades = len(trades)
    total_return = ((equity - capital) / capital) * 100
    win_rate = 0.0
    profit_factor = 1.0
    sharpe = 0.0

    if num_trades > 0:
        wins = sum(1 for t in trades if t.pnl > 0)
        win_rate = (wins / num_trades) * 100
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        returns = [t.pnl_pct for t in trades]
        if returns:
            avg_r = sum(returns) / len(returns)
            std_r = statistics.stdev(returns) if len(returns) > 1 else 0.001
            sharpe = (avg_r / std_r * (252 ** 0.5)) if std_r > 0 else 0

    return BacktestResponse(
        strategy=strategy,
        symbol=candles[-1].get("symbol", "unknown") if candles else "unknown",
        total_return=round(total_return, 2),
        win_rate=round(win_rate, 1),
        profit_factor=round(profit_factor, 2),
        max_drawdown=round(max_dd * 100, 2),
        num_trades=num_trades,
        sharpe_ratio=round(sharpe, 2),
        trades=trades,
    )


def _generate_signal_for_backtest(closes, highs, lows, idx, candles, strategy):
    if idx < 100:
        return None
    fake_candles = candles[:idx + 1]
    if strategy == "momentum":
        sig = _momentum_signal(fake_candles)
    elif strategy == "mean_reversion":
        sig = _mean_reversion_signal(fake_candles)
    elif strategy == "scalping":
        sig = _scalping_signal(fake_candles)
    else:
        from app.engine.signals import generate_signal
        sig = generate_signal(fake_candles, "adaptive")
    action = sig.get("action", "HOLD")
    if action == "BUY":
        return "buy"
    elif action == "SELL":
        return "sell"
    return None

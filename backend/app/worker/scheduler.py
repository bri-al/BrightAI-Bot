import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func

from app.config import settings
from app.database import async_session
from app.models import Trade
from app.risk.manager import risk_engine
from app.execution.executor import get_executor
from app.engine.market import market_data
from app.engine.signals import generate_signal
from app.engine.regime import detect_regime
from app.engine.indicators import atr, sma
from app.strategies.base import strategy_manager

logger = logging.getLogger("scheduler")


def _classify_symbol(symbol: str) -> str:
    if symbol in settings.crypto_symbols:
        return "crypto"
    if symbol in settings.forex_symbols:
        return "forex"
    if symbol in settings.stock_symbols:
        return "stock"
    if symbol.endswith("USDT"):
        return "crypto"
    return "other"


class TradingScheduler:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Scheduler started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Scheduler stopped")

    async def _loop(self):
        while self._running:
            try:
                if risk_engine.is_trading and not risk_engine.kill_switch:
                    await self._scan_markets()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(settings.scan_interval_seconds)

    async def _scan_markets(self):
        async with async_session() as db:
            executor = get_executor()

            broker_positions = await executor.get_all_positions()
            risk_engine.sync_from_broker(broker_positions)

            broker_account = await executor.get_account()
            if broker_account.get("balance", 0) > 0:
                risk_engine.sync_account(broker_account["balance"], broker_account["equity"])

            for symbol in settings.all_symbols:
                try:
                    candles = await market_data.fetch_historical(symbol, limit=200)
                    if len(candles) < 50:
                        continue

                    sym_strategy = settings.get_strategy(symbol)
                    trend_direction = None
                    if sym_strategy == "momentum_tf":
                        try:
                            candles_1h = await market_data.fetch_historical(symbol, timeframe="1h", limit=100)
                            if len(candles_1h) >= 50:
                                closes_1h = [c["close"] for c in candles_1h]
                                s50_1h = sma(closes_1h, 50)[-1] if sma(closes_1h, 50)[-1] else closes_1h[-1]
                                s20_1h = sma(closes_1h, 20)[-1] if sma(closes_1h, 20)[-1] else closes_1h[-1]
                                p1h = closes_1h[-1]
                                if p1h > s50_1h * 1.005 and p1h > s20_1h:
                                    trend_direction = "uptrend"
                                elif p1h < s50_1h * 0.995 and p1h < s20_1h:
                                    trend_direction = "downtrend"
                                else:
                                    trend_direction = "neutral"
                        except Exception:
                            pass
                    signal = generate_signal(candles, sym_strategy, trend_direction=trend_direction)
                    if signal["action"] == "HOLD" or signal["confidence"] < settings.min_confidence:
                        continue

                    price = signal["price"]
                    direction = "long" if signal["action"] == "BUY" else "short"
                    highs_s = [c["high"] for c in candles]
                    lows_s = [c["low"] for c in candles]
                    closes_s = [c["close"] for c in candles]
                    atr_vals_local = atr(highs_s, lows_s, closes_s, 14)
                    atr_val_local = atr_vals_local[-1] if atr_vals_local[-1] is not None else price * 0.02
                    if sym_strategy == "scalping":
                        sl = price - 0.5 * atr_val_local if direction == "long" else price + 0.5 * atr_val_local
                        tp = price + 1.0 * atr_val_local if direction == "long" else price - 1.0 * atr_val_local
                    else:
                        sl = price - 1.5 * atr_val_local if direction == "long" else price + 1.5 * atr_val_local
                        tp = price + 3.0 * atr_val_local if direction == "long" else price - 3.0 * atr_val_local

                    open_count = await db.scalar(
                        select(func.count(Trade.id)).where(Trade.status == "open")
                    ) or 0

                    regime_name = signal.get("regime", "unknown")
                    valid, msg = risk_engine.validate_trade(price, sl, tp, direction, open_count, symbol)
                    if not valid:
                        logger.info(f"Trade rejected for {symbol}: {msg}")
                        continue

                    size = risk_engine.calculate_position_size(price, sl, direction, regime=regime_name)
                    executor = get_executor()
                    side = "buy" if direction == "long" else "sell"
                    order = await executor.market_order(symbol, side, size, sl=sl, tp=tp)

                    if order.success:
                        trade = Trade(
                            symbol=symbol,
                            asset_class=_classify_symbol(symbol),
                            direction=direction,
                            entry_price=order.filled_price,
                            size=order.filled_size,
                            stop_loss=sl,
                            take_profit=tp,
                            status="open",
                            strategy=sym_strategy,
                            signal_reason=signal["reason"],
                            confidence=signal["confidence"],
                            broker_order_id=order.order_id,
                        )
                        db.add(trade)
                        await db.commit()

                        risk_engine.open_trade(symbol, direction, order.filled_price, sl, tp, order.filled_size, sym_strategy, atr_value=atr_val_local)

                        logger.info(
                            f"Executed {direction} {symbol} @ {order.filled_price:.2f} "
                            f"size={order.filled_size:.4f} confidence={signal['confidence']}"
                        )
                        await self._broadcast_trade(symbol, signal, order)
                    else:
                        logger.warning(f"Order failed for {symbol}: {order.message}")
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")

            market_prices = {}
            for sym in settings.all_symbols:
                try:
                    price = await executor.get_price(sym)
                    if price > 0:
                        market_prices[sym] = price
                except Exception:
                    pass
            closed_before = len(risk_engine.recently_closed)
            risk_engine.update_positions(market_prices)
            await self._persist_closed_positions(db, closed_before)

            broker_account = await executor.get_account()
            if broker_account.get("balance", 0) > 0:
                risk_engine.sync_account(broker_account["balance"], broker_account["equity"])

    async def _persist_closed_positions(self, db, closed_before: int):
        for entry in risk_engine.recently_closed[closed_before:]:
            try:
                result = await db.execute(
                    select(Trade).where(
                        Trade.symbol == entry["symbol"],
                        Trade.status == "open",
                    ).order_by(Trade.created_at.desc()).limit(1)
                )
                trade = result.scalar_one_or_none()
                if trade:
                    trade.exit_price = entry["exit"]
                    trade.pnl = entry["pnl"]
                    trade.pnl_pct = round(entry["pnl"] / (entry["entry"] * entry["size"]) * 100, 2) if entry["entry"] * entry["size"] > 0 else 0
                    trade.status = "closed"
                    trade.exit_reason = "trailing_stop"
                await db.commit()
            except Exception:
                await db.rollback()

    async def _broadcast_trade(self, symbol: str, signal: dict, order):
        try:
            from app.routers.ws import broadcast
            await broadcast({
                "type": "trade_executed",
                "data": {
                    "symbol": symbol,
                    "action": signal["action"],
                    "price": order.filled_price,
                    "size": order.filled_size,
                    "confidence": signal["confidence"],
                    "regime": signal["regime"],
                    "reason": signal["reason"],
                },
            })
        except Exception:
            pass


scheduler = TradingScheduler()

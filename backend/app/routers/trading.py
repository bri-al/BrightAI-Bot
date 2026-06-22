from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Trade
from app.schemas import TradeResponse
from app.risk.manager import risk_engine
from app.execution.executor import get_executor
from app.engine.market import market_data
from app.engine.signals import generate_signal
from app.engine.regime import detect_regime
from app.engine.indicators import atr, sma
from app.worker.scheduler import scheduler
from app.auth import verify_api_key
from app.config import settings

router = APIRouter(prefix="/trade", tags=["Trading"])


@router.post("/start")
async def start_trading(auth: str = Depends(verify_api_key)):
    if risk_engine.kill_switch:
        raise HTTPException(400, "Kill switch is active. Reset to start.")
    risk_engine.is_trading = True
    await scheduler.start()
    return {"status": "started", "message": "Trading bot activated"}


@router.post("/stop")
async def stop_trading(auth: str = Depends(verify_api_key)):
    risk_engine.is_trading = False
    await scheduler.stop()
    return {"status": "stopped", "message": "Trading bot deactivated"}


@router.post("/pause")
async def pause_trading(auth: str = Depends(verify_api_key)):
    risk_engine.is_trading = False
    return {"status": "paused", "message": "Trading paused"}


@router.post("/resume")
async def resume_trading(auth: str = Depends(verify_api_key)):
    if risk_engine.kill_switch:
        raise HTTPException(400, "Kill switch is active")
    risk_engine.is_trading = True
    return {"status": "resumed", "message": "Trading resumed"}


@router.post("/kill")
async def kill_switch(auth: str = Depends(verify_api_key)):
    risk_engine.kill_switch = True
    risk_engine.is_trading = False
    await scheduler.stop()
    return {"status": "killed", "message": "Emergency kill switch activated - all trading stopped"}


@router.post("/kill/reset")
async def reset_kill_switch(auth: str = Depends(verify_api_key)):
    risk_engine.kill_switch = False
    return {"status": "reset", "message": "Kill switch reset"}


@router.post("/clear-positions")
async def clear_positions(auth: str = Depends(verify_api_key)):
    risk_engine.active_positions.clear()
    risk_engine.open_positions = 0
    return {"status": "cleared", "message": "All open positions cleared from risk engine"}


@router.post("/reset-drawdown")
async def reset_drawdown(auth: str = Depends(verify_api_key)):
    risk_engine.peak_equity = risk_engine.current_equity
    risk_engine.drawdown = 0.0
    return {"status": "reset", "peak_equity": risk_engine.peak_equity, "message": "Drawdown tracker reset"}


@router.get("/status")
async def trading_status():
    exec = get_executor()
    try:
        account = await exec.get_account()
    except Exception:
        account = {"balance": 0, "equity": 0, "margin": 0, "profit": 0}
    return {
        "is_trading": risk_engine.is_trading,
        "kill_switch": risk_engine.kill_switch,
        "active_strategy": risk_engine.to_dict(),
        "broker": {
            "name": exec.broker_name,
            "connected": exec.connected,
            "account": account,
        },
    }


@router.post("/execute/{symbol}")
async def execute_trade(symbol: str, db: AsyncSession = Depends(get_db), auth: str = Depends(verify_api_key)):
    if not risk_engine.is_trading and not risk_engine.kill_switch:
        raise HTTPException(400, "Trading is not active")

    candles = await market_data.fetch_historical(symbol, limit=200)
    if len(candles) < 50:
        raise HTTPException(400, "Insufficient market data")

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
        return {"action": "HOLD", "reason": signal["reason"], "confidence": signal["confidence"]}

    open_count = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "open")
    ) or 0
    price = signal["price"]
    direction = "long" if signal["action"] == "BUY" else "short"
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]
    atr_vals = atr(highs, lows, closes, 14)
    atr_val = atr_vals[-1] if atr_vals[-1] is not None else price * 0.02
    if sym_strategy == "scalping":
        sl = price - 0.5 * atr_val if direction == "long" else price + 0.5 * atr_val
        tp = price + 1.0 * atr_val if direction == "long" else price - 1.0 * atr_val
    else:
        sl = price - 1.5 * atr_val if direction == "long" else price + 1.5 * atr_val
        tp = price + 3.0 * atr_val if direction == "long" else price - 3.0 * atr_val

    regime_name = signal.get("regime", "unknown")
    valid, msg = risk_engine.validate_trade(price, sl, tp, direction, open_count, symbol)
    if not valid:
        return {"action": "REJECTED", "reason": msg}

    size = risk_engine.calculate_position_size(price, sl, direction, regime=regime_name)

    executor = get_executor()
    side = "buy" if direction == "long" else "sell"
    order = await executor.market_order(symbol, side, size, sl=sl, tp=tp)
    if not order.success:
        return {"action": "FAILED", "reason": order.message}

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
    await db.refresh(trade)

    risk_engine.open_trade(symbol, direction, order.filled_price, sl, tp, order.filled_size, sym_strategy)

    return {
        "action": signal["action"],
        "trade_id": trade.id,
        "entry": order.filled_price,
        "size": order.filled_size,
        "confidence": signal["confidence"],
        "regime": signal["regime"],
        "reason": signal["reason"],
    }


def _classify_symbol(symbol: str) -> str:
    from app.config import settings
    if symbol in settings.crypto_symbols:
        return "crypto"
    if symbol in settings.forex_symbols:
        return "forex"
    if symbol in settings.stock_symbols:
        return "stock"
    if symbol.endswith("USDT"):
        return "crypto"
    return "other"

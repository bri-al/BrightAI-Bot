from fastapi import APIRouter, HTTPException

from app.engine.market import market_data
from app.engine.signals import generate_signal
from app.engine.indicators import rsi, volatility
from app.engine.regime import detect_regime
from app.config import settings

analysis_router = APIRouter(prefix="/analysis", tags=["Analysis"])
signal_router = APIRouter(prefix="/signal", tags=["Signals"])


@analysis_router.get("/{symbol}")
async def get_analysis(symbol: str):
    candles = await market_data.fetch_historical(symbol, limit=200)
    if len(candles) < 50:
        raise HTTPException(400, "Insufficient market data")

    closes = [c["close"] for c in candles]
    current_price = closes[-1]
    regime_info = detect_regime(candles)
    rsi_vals = rsi(closes, 14)
    rsi_val = round(rsi_vals[-1], 1) if rsi_vals[-1] is not None else 50
    vol = volatility(closes, 20)
    vol_val = vol[-1] if vol[-1] is not None else 0

    bias = "neutral"
    if rsi_val > 60:
        bias = "long"
    elif rsi_val < 40:
        bias = "short"

    vol_level = "low"
    vol_vals = [v for v in vol if v is not None]
    if vol_vals:
        avg_vol = sum(vol_vals) / max(len(vol_vals), 1)
        if vol_val > avg_vol * 1.5:
            vol_level = "high"
        elif vol_val > avg_vol * 1.2:
            vol_level = "medium"

    return {
        "symbol": symbol,
        "current_price": current_price,
        "trend": regime_info.get("trend", "neutral"),
        "regime": regime_info.get("regime", "unknown"),
        "rsi": rsi_val,
        "bias": bias,
        "volatility_level": vol_level,
        "volatility_ratio": regime_info.get("volatility_ratio", 1.0),
    }


@signal_router.get("/{symbol}")
async def get_signal(symbol: str):
    candles = await market_data.fetch_historical(symbol, limit=200)
    if len(candles) < 50:
        raise HTTPException(400, "Insufficient market data")

    signal = generate_signal(candles, settings.strategy)
    return signal


from fastapi import APIRouter as MarketRouter

market_router = MarketRouter(prefix="/market", tags=["Market"])


@market_router.get("/candles/{symbol}")
async def get_candles(symbol: str, limit: int = 100):
    candles = await market_data.fetch_historical(symbol, limit=limit)
    if len(candles) < 2:
        raise HTTPException(400, "Insufficient market data")
    return {
        "symbol": symbol,
        "candles": [
            {
                "time": int(
                    __import__("datetime").datetime.fromisoformat(c["timestamp"]).timestamp()
                ),
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": c.get("volume", 0),
            }
            for c in candles[-limit:]
        ],
    }

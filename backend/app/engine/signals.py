from app.engine.indicators import rsi, macd, bollinger_bands, sma, ema, adx, atr, detect_divergence
from app.engine.regime import detect_regime
from app.engine.confidence import score_confidence


def generate_signal(candles: list[dict], strategy: str = "adaptive", trend_direction: str | None = None) -> dict:
    if len(candles) < 100:
        return {
            "action": "HOLD",
            "confidence": 0,
            "regime": "unknown",
            "reason": "insufficient data",
            "price": candles[-1]["close"] if candles else 0,
        }

    regime_info = detect_regime(candles)
    regime = regime_info["regime"]
    adx_val = regime_info.get("adx", 0)
    atr_pct = regime_info.get("atr_pct", 2)
    vol_ratio = regime_info.get("volatility_ratio", 1)

    if strategy == "adaptive":
        if regime in ("strong_trend", "trend"):
            signal = _momentum_signal(candles, regime_info)
        elif regime in ("range", "neutral"):
            signal = _mean_reversion_signal(candles, regime_info)
        elif regime in ("volatile", "choppy"):
            signal = _scalping_signal(candles, regime_info)
        elif regime == "weak_trend":
            signal = _momentum_signal(candles, regime_info)
        else:
            signal = _momentum_signal(candles, regime_info)
    elif strategy == "momentum":
        signal = _momentum_signal(candles, regime_info)
    elif strategy == "momentum_tf":
        signal = _momentum_signal(candles, regime_info)
        if trend_direction == "uptrend" and signal["action"] == "SELL":
            signal = {"action": "HOLD", "confidence": 0, "reason": "Counter-trend filtered by 1h uptrend"}
        elif trend_direction == "downtrend" and signal["action"] == "BUY":
            signal = {"action": "HOLD", "confidence": 0, "reason": "Counter-trend filtered by 1h downtrend"}
    elif strategy == "mean_reversion":
        signal = _mean_reversion_signal(candles, regime_info)
    elif strategy == "scalping":
        signal = _scalping_signal(candles, regime_info)
    else:
        signal = {"action": "HOLD", "reason": "unknown strategy"}

    action = signal.get("action", "HOLD")
    raw_confidence = signal.get("confidence", 50)
    reason = signal.get("reason", "")

    if adx_val < 20 and regime == "weak_trend" and action != "HOLD":
        raw_confidence = max(raw_confidence * 0.7, 15)

    confidence = score_confidence(action, raw_confidence, regime_info, candles)

    return {
        "action": action,
        "confidence": confidence,
        "regime": regime,
        "regime_strength": regime_info["strength"],
        "reason": reason,
        "price": candles[-1]["close"],
    }


def _momentum_signal(candles: list[dict], regime: dict | None = None) -> dict:
    if regime is None:
        regime = {"regime": "unknown", "adx": 0, "volatility_ratio": 1, "atr_pct": 2}
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c.get("volume", 0) for c in candles]

    fast_ema = ema(closes, 9)
    slow_ema = ema(closes, 21)
    rsi_vals = rsi(closes, 14)
    adx_vals = adx(highs, lows, closes, 14)
    macd_line, signal_line, histogram = macd(closes, 12, 26, 9)

    fe = fast_ema[-1] if fast_ema[-1] is not None else closes[-1]
    se = slow_ema[-1] if slow_ema[-1] is not None else closes[-1]
    fe_prev = fast_ema[-2] if len(fast_ema) > 1 and fast_ema[-2] is not None else fe
    se_prev = slow_ema[-2] if len(slow_ema) > 1 and slow_ema[-2] is not None else se
    rsi_val = rsi_vals[-1] if rsi_vals[-1] is not None else 50
    rsi_prev = rsi_vals[-2] if len(rsi_vals) > 1 and rsi_vals[-2] is not None else 50
    adx_val = adx_vals[-1] if adx_vals[-1] is not None else 0
    mac = macd_line[-1] if macd_line[-1] is not None else 0
    sig = signal_line[-1] if signal_line[-1] is not None else 0
    mac_prev = macd_line[-2] if len(macd_line) > 1 and macd_line[-2] is not None else mac
    sig_prev = signal_line[-2] if len(signal_line) > 1 and signal_line[-2] is not None else sig
    hist_val = histogram[-1] if histogram[-1] is not None else 0
    hist_prev = histogram[-2] if len(histogram) > 1 and histogram[-2] is not None else 0

    price = closes[-1]

    rsi_div_bearish = detect_divergence(closes, rsi_vals, 30) == "bearish"
    rsi_div_bullish = detect_divergence(closes, rsi_vals, 30) == "bullish"
    macd_div_bearish = detect_divergence(closes, macd_line, 30) == "bearish"
    macd_div_bullish = detect_divergence(closes, macd_line, 30) == "bullish"

    volume_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / max(len(volumes), 1)
    volume_surge = volumes[-1] > volume_avg * 1.5 if volumes else False

    trend_strength = adx_val / 50

    def buy_signals() -> list[str]:
        sigs = []
        if fe > se and fe_prev <= se_prev:
            sigs.append("ema_cross")
        if rsi_val > 50 and rsi_prev <= 50:
            sigs.append("rsi_mid")
        if mac > sig and mac_prev <= sig_prev:
            sigs.append("macd_cross")
        if hist_val > 0 and hist_prev <= 0:
            sigs.append("macd_hist")
        if volume_surge and closes[-1] > closes[-2]:
            sigs.append("vol_surge")
        return sigs

    def sell_signals() -> list[str]:
        sigs = []
        if fe < se and fe_prev >= se_prev:
            sigs.append("ema_cross")
        if rsi_val < 50 and rsi_prev >= 50:
            sigs.append("rsi_mid")
        if mac < sig and mac_prev >= sig_prev:
            sigs.append("macd_cross")
        if hist_val < 0 and hist_prev >= 0:
            sigs.append("macd_hist")
        if volume_surge and closes[-1] < closes[-2]:
            sigs.append("vol_surge")
        return sigs

    buys = buy_signals()
    sells = sell_signals()
    num_buys = len(buys)
    num_sells = len(sells)

    if rsi_div_bullish and buys:
        return {"action": "BUY", "confidence": 85, "reason": f"Bullish divergence + {num_buys} signals"}
    if rsi_div_bearish and sells:
        return {"action": "SELL", "confidence": 85, "reason": f"Bearish divergence + {num_sells} signals"}

    if macd_div_bullish and buys:
        return {"action": "BUY", "confidence": 80, "reason": f"MACD bull divergence + {num_buys} signals"}
    if macd_div_bearish and sells:
        return {"action": "SELL", "confidence": 80, "reason": f"MACD bear divergence + {num_sells} signals"}

    if num_buys >= 2:
        conf = 60 + min(num_buys * 8, 25) + (10 if trend_strength > 0.5 else 0)
        return {"action": "BUY", "confidence": conf, "reason": f"Momentum confluence ({num_buys} signals)"}

    if num_sells >= 2:
        conf = 60 + min(num_sells * 8, 25) + (10 if trend_strength > 0.5 else 0)
        return {"action": "SELL", "confidence": conf, "reason": f"Momentum confluence ({num_sells} signals)"}

    if "ema_cross" in buys or "macd_cross" in buys:
        return {"action": "BUY", "confidence": 50, "reason": "Single momentum trigger"}
    if "ema_cross" in sells or "macd_cross" in sells:
        return {"action": "SELL", "confidence": 50, "reason": "Single momentum trigger"}

    if fe > se and rsi_val > 55:
        return {"action": "BUY", "confidence": 45, "reason": "Trend up, RSI confirms"}
    if fe < se and rsi_val < 45:
        return {"action": "SELL", "confidence": 45, "reason": "Trend down, RSI confirms"}

    return {"action": "HOLD", "confidence": 30, "reason": "No clear momentum confluence"}


def _mean_reversion_signal(candles: list[dict], regime: dict | None = None) -> dict:
    if regime is None:
        regime = {}
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    rsi_vals = rsi(closes, 14)
    bb_upper, bb_mid, bb_lower = bollinger_bands(closes)
    rsi_val = rsi_vals[-1] if rsi_vals[-1] is not None else 50
    rsi_prev = rsi_vals[-2] if len(rsi_vals) > 1 and rsi_vals[-2] is not None else 50
    price = closes[-1]
    lower = bb_lower[-1] if bb_lower[-1] is not None else price * 0.95
    upper = bb_upper[-1] if bb_upper[-1] is not None else price * 1.05
    mid_bb = bb_mid[-1] if bb_mid[-1] is not None else price

    rsi_div_bearish = detect_divergence(closes, rsi_vals, 25) == "bearish"
    rsi_div_bullish = detect_divergence(closes, rsi_vals, 25) == "bullish"

    bb_range = upper - lower

    z_score = (price - mid_bb) / max(bb_range / 4, price * 0.001)

    if rsi_val < 30 and price <= lower and rsi_val > rsi_prev:
        conf = 80
        reason = f"Oversold (RSI={rsi_val:.1f}) at lower BB"
        if rsi_div_bullish:
            conf = 92
            reason += " + bullish divergence"
        elif rsi_val < 25:
            conf += 10
        return {"action": "BUY", "confidence": conf, "reason": reason}
    if rsi_val > 70 and price >= upper and rsi_val < rsi_prev:
        conf = 80
        reason = f"Overbought (RSI={rsi_val:.1f}) at upper BB"
        if rsi_div_bearish:
            conf = 92
            reason += " + bearish divergence"
        elif rsi_val > 75:
            conf += 10
        return {"action": "SELL", "confidence": conf, "reason": reason}

    if rsi_div_bullish and price < mid_bb:
        return {"action": "BUY", "confidence": 75, "reason": "Bullish divergence below midline"}
    if rsi_div_bearish and price > mid_bb:
        return {"action": "SELL", "confidence": 75, "reason": "Bearish divergence above midline"}

    if rsi_val < 32:
        return {"action": "BUY", "confidence": 60, "reason": f"Approaching oversold (RSI={rsi_val:.1f})"}
    if rsi_val > 68:
        return {"action": "SELL", "confidence": 60, "reason": f"Approaching overbought (RSI={rsi_val:.1f})"}

    if z_score < -2.5:
        return {"action": "BUY", "confidence": 55, "reason": f"Extreme BB deviation (z={z_score:.1f})"}
    if z_score > 2.5:
        return {"action": "SELL", "confidence": 55, "reason": f"Extreme BB deviation (z={z_score:.1f})"}

    return {"action": "HOLD", "confidence": 30, "reason": "No mean reversion opportunity"}


def _scalping_signal(candles: list[dict], regime: dict | None = None) -> dict:
    if regime is None:
        regime = {}
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    rsi_vals = rsi(closes, 7)
    macd_line, signal_line, histogram = macd(closes, 6, 13, 5)
    atr_vals = atr(highs, lows, closes, 7)

    rsi_val = rsi_vals[-1] if rsi_vals[-1] is not None else 50
    mac = macd_line[-1] if macd_line[-1] is not None else 0
    sig = signal_line[-1] if signal_line[-1] is not None else 0
    mac_prev = macd_line[-2] if len(macd_line) > 1 and macd_line[-2] is not None else mac
    sig_prev = signal_line[-2] if len(signal_line) > 1 and signal_line[-2] is not None else sig
    hist_val = histogram[-1] if histogram[-1] is not None else 0
    hist_prev = histogram[-2] if len(histogram) > 1 and histogram[-2] is not None else 0
    atr_val = atr_vals[-1] if atr_vals[-1] is not None else (closes[-1] * 0.015)
    atr_pct = atr_val / closes[-1] * 100 if closes[-1] > 0 else 1.5

    if atr_pct < 0.1 or atr_pct > 5:
        return {"action": "HOLD", "confidence": 15, "reason": f"ATR={atr_pct:.1f}% outside scalp range"}

    buy_score = 0
    sell_score = 0
    reasons = []

    if mac > sig and mac_prev <= sig_prev:
        buy_score += 3
        reasons.append("MACD_cross")
    if mac < sig and mac_prev >= sig_prev:
        sell_score += 3
        reasons.append("MACD_cross")

    if hist_val > 0 and hist_prev <= 0:
        buy_score += 2
        reasons.append("hist_turn")
    if hist_val < 0 and hist_prev >= 0:
        sell_score += 2
        reasons.append("hist_turn")

    if rsi_val < 30:
        buy_score += 3
        reasons.append("RSI_oversold")
    elif rsi_val < 40:
        buy_score += 1
        reasons.append("RSI_low")
    elif rsi_val > 70:
        sell_score += 3
        reasons.append("RSI_overbought")
    elif rsi_val > 60:
        sell_score += 1
        reasons.append("RSI_high")

    if closes[-1] > closes[-2]:
        buy_score += 1
    else:
        sell_score += 1

    if buy_score >= 4:
        return {"action": "BUY", "confidence": min(50 + buy_score * 10, 95), "reason": f"Scalp buy: {', '.join(reasons)}"}
    if sell_score >= 4:
        return {"action": "SELL", "confidence": min(50 + sell_score * 10, 95), "reason": f"Scalp sell: {', '.join(reasons)}"}

    return {"action": "HOLD", "confidence": 20, "reason": "No scalping opportunity"}

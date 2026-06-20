from app.engine.indicators import sma, ema, volatility, adx, atr, bollinger_bands


def detect_regime(candles: list[dict]) -> dict:
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    n = len(closes)

    if n < 50:
        return {"regime": "unknown", "strength": 0, "reason": "insufficient data"}

    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    sma100 = sma(closes, 100)
    vol = volatility(closes, 20)
    adx_vals = adx(highs, lows, closes, 14)
    atr_vals = atr(highs, lows, closes, 14)

    current_price = closes[-1]
    sma20_val = sma20[-1] if sma20[-1] is not None else current_price
    sma50_val = sma50[-1] if sma50[-1] is not None else current_price
    sma100_val = sma100[-1] if sma100[-1] is not None else current_price

    adx_val = adx_vals[-1] if adx_vals[-1] is not None else 0
    atr_val = atr_vals[-1] if atr_vals[-1] is not None else (current_price * 0.02)
    atr_pct = atr_val / current_price if current_price > 0 else 0.02

    higher_tf_trend = 0
    if sma50_val is not None and sma100_val is not None:
        if sma50_val > sma100_val * 1.01:
            higher_tf_trend = 1
        elif sma50_val < sma100_val * 0.99:
            higher_tf_trend = -1

    mid_tf_trend = 0
    if current_price is not None and sma50_val is not None:
        if current_price > sma50_val * 1.01:
            mid_tf_trend = 1
        elif current_price < sma50_val * 0.99:
            mid_tf_trend = -1

    trend_bias = 1 if mid_tf_trend > 0 and higher_tf_trend >= 0 else (-1 if mid_tf_trend < 0 and higher_tf_trend <= 0 else 0)
    if mid_tf_trend == 1 and higher_tf_trend == 0:
        trend_bias = 1
    elif mid_tf_trend == -1 and higher_tf_trend == 0:
        trend_bias = -1
    elif mid_tf_trend == 0 and higher_tf_trend != 0:
        trend_bias = higher_tf_trend

    vol_vals = [v for v in vol if v is not None]
    avg_vol = sum(vol_vals) / max(len(vol_vals), 1) if vol_vals else 0.0001
    latest_vol = vol[-1] if vol[-1] is not None else avg_vol
    vol_ratio = latest_vol / max(avg_vol, 0.0001)

    price_position = 0
    if current_price > sma20_val > sma50_val:
        price_position = 2
    elif current_price > sma20_val and current_price > sma50_val:
        price_position = 1
    elif current_price < sma20_val < sma50_val:
        price_position = -2
    elif current_price < sma20_val and current_price < sma50_val:
        price_position = -1

    relative_strength = (current_price - sma50_val) / max(sma50_val, 0.01) * 100 if sma50_val else 0

    bb_upper, bb_mid, bb_lower = bollinger_bands(closes, 20, 2.0)
    bb_mid_val = bb_mid[-1] if bb_mid[-1] is not None else sma20_val
    bb_upper_val = bb_upper[-1] if bb_upper[-1] is not None else current_price * 1.02
    bb_lower_val = bb_lower[-1] if bb_lower[-1] is not None else current_price * 0.98
    bb_width_pct = (bb_upper_val - bb_lower_val) / max(bb_mid_val, 0.01) * 100 if bb_mid_val else 0

    if adx_val >= 25:
        if abs(price_position) >= 1 and vol_ratio < 1.3:
            regime = "strong_trend"
            strength = min(adx_val * 2.5, 99)
            dir_str = "bullish" if price_position > 0 else "bearish"
            reason = f"Strong {dir_str} trend (ADX={adx_val:.0f})"
        elif abs(price_position) >= 1:
            regime = "trend"
            strength = min(adx_val * 2, 90)
            dir_str = "bullish" if price_position > 0 else "bearish"
            reason = f"{dir_str.capitalize()} trend with elevated volatility (ADX={adx_val:.0f})"
        else:
            regime = "weak_trend"
            strength = min(adx_val * 1.5, 70)
            reason = f"Price not aligned with MAs despite ADX={adx_val:.0f}"
    elif vol_ratio > 1.8:
        regime = "volatile"
        strength = min(vol_ratio * 25, 85)
        reason = f"High volatility ({vol_ratio:.1f}x avg)"
    elif bb_width_pct < 5 and abs(relative_strength) < 2:
        regime = "range"
        strength = max(60 - abs(relative_strength) * 10, 30)
        reason = f"Tight range (BB width={bb_width_pct:.1f}%)"
    elif vol_ratio > 1.3:
        regime = "choppy"
        strength = min(vol_ratio * 20, 60)
        reason = f"Choppy market (vol={vol_ratio:.1f}x)"
    elif abs(price_position) >= 1:
        regime = "trend"
        strength = min(abs(relative_strength) * 15, 80) + 10
        dir_str = "bullish" if price_position > 0 else "bearish"
        reason = f"Developing {dir_str} trend"
    else:
        regime = "neutral"
        strength = 25
        reason = "No clear regime detected"

    if trend_bias > 0:
        trend = "bullish"
    elif trend_bias < 0:
        trend = "bearish"
    else:
        trend = "neutral"

    return {
        "regime": regime,
        "strength": round(strength, 1),
        "reason": reason,
        "volatility_ratio": round(vol_ratio, 2),
        "price": current_price,
        "trend": trend,
        "adx": round(adx_val, 1),
        "atr_pct": round(atr_pct * 100, 2),
        "bb_width_pct": round(bb_width_pct, 2),
    }

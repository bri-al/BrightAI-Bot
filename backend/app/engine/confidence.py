from app.config import settings
from app.engine.indicators import atr


def score_confidence(
    action: str,
    raw_confidence: float,
    regime_info: dict,
    candles: list[dict],
) -> int:
    if action == "HOLD":
        return 0

    score = float(raw_confidence)
    regime = regime_info.get("regime", "unknown")
    trend = regime_info.get("trend", "neutral")
    strength = regime_info.get("strength", 0)

    if regime in ("strong_trend", "trend"):
        if (action == "BUY" and trend == "bullish") or (action == "SELL" and trend == "bearish"):
            score += 12
        elif (action == "BUY" and trend == "bearish") or (action == "SELL" and trend == "bullish"):
            score -= 20

    if regime == "range":
        score += 5

    if regime == "weak_trend":
        score -= 8
    if regime in ("volatile", "choppy"):
        score -= 12

    if strength > 70:
        score += 8
    elif strength < 25:
        score -= 8

    if len(candles) > 25:
        volumes = [c.get("volume", 0) for c in candles[-25:]]
        avg_vol = sum(volumes) / max(len(volumes), 1)
        last_vol = candles[-1].get("volume", 0)
        if avg_vol > 0:
            vol_ratio = last_vol / avg_vol
            if vol_ratio > 1.5:
                score += 10
            elif vol_ratio > 1.2:
                score += 4
            elif vol_ratio < 0.5:
                score -= 8
            elif vol_ratio < 0.7:
                score -= 3

    vol_trend = 0
    if len(candles) > 50:
        vol_short = [c.get("volume", 0) for c in candles[-10:]]
        vol_long = [c.get("volume", 0) for c in candles[-50:-10]]
        avg_short = sum(vol_short) / max(len(vol_short), 1)
        avg_long = sum(vol_long) / max(len(vol_long), 1)
        if avg_long > 0:
            vol_trend = (avg_short / avg_long - 1) * 100
            if vol_trend > 20:
                score += 6
            elif vol_trend < -20:
                score -= 4

    closes = [c["close"] for c in candles]
    if len(closes) > 20:
        atr_vals = atr(
            [c.get("high", c["close"]) for c in candles],
            [c.get("low", c["close"]) for c in candles],
            closes, 14
        )
        atr_val = atr_vals[-1] if atr_vals[-1] is not None else 0
        atr_pct = atr_val / closes[-1] * 100 if closes[-1] > 0 else 0
        if atr_pct > 5:
            score -= 10
        elif atr_pct < 0.5:
            score -= 5

    score = max(0, min(100, int(score)))

    if score < settings.min_confidence:
        return 0

    return score

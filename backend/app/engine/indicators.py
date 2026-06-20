import math
import statistics
from typing import Optional


def sma(data: list[float], period: int) -> list[Optional[float]]:
    result: list[Optional[float]] = []
    for i in range(len(data)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(sum(data[i - period + 1: i + 1]) / period)
    return result


def ema(data: list[float], period: int) -> list[Optional[float]]:
    result: list[Optional[float]] = []
    multiplier = 2 / (period + 1)
    for i in range(len(data)):
        if i < period - 1:
            result.append(None)
        elif i == period - 1:
            result.append(sum(data[:period]) / period)
        else:
            prev = result[-1]
            if prev is None:
                result.append(None)
            else:
                result.append((data[i] - prev) * multiplier + prev)
    return result


def rsi(data: list[float], period: int = 14) -> list[Optional[float]]:
    if len(data) < period + 1:
        return [None] * len(data)
    result: list[Optional[float]] = [None] * period
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        diff = data[i] - data[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        result.append(100.0)
    else:
        result.append(100.0 - 100.0 / (1.0 + avg_gain / avg_loss))
    for i in range(period + 1, len(data)):
        diff = data[i] - data[i - 1]
        if diff >= 0:
            avg_gain = (avg_gain * (period - 1) + diff) / period
            avg_loss = (avg_loss * (period - 1)) / period
        else:
            avg_gain = (avg_gain * (period - 1)) / period
            avg_loss = (avg_loss * (period - 1) - diff) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            result.append(100.0 - 100.0 / (1.0 + avg_gain / avg_loss))
    return result


def macd(data: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    macd_line: list[Optional[float]] = []
    for i in range(len(data)):
        if ema_fast[i] is None or ema_slow[i] is None:
            macd_line.append(None)
        else:
            macd_line.append(ema_fast[i] - ema_slow[i])
    first_valid = next((i for i, v in enumerate(macd_line) if v is not None), len(data))
    valid_part = macd_line[first_valid:]
    if valid_part:
        signal_valid = ema(valid_part, signal)
        signal_line = [None] * first_valid + signal_valid
    else:
        signal_line = [None] * len(data)
    histogram: list[Optional[float]] = []
    for i in range(len(data)):
        if macd_line[i] is None or signal_line[i] is None:
            histogram.append(None)
        else:
            histogram.append(macd_line[i] - signal_line[i])
    return macd_line, signal_line, histogram


def bollinger_bands(data: list[float], period: int = 20, std_dev: float = 2.0):
    mid = sma(data, period)
    upper: list[Optional[float]] = []
    lower: list[Optional[float]] = []
    for i in range(len(data)):
        if mid[i] is None:
            upper.append(None)
            lower.append(None)
            continue
        window = data[max(0, i - period + 1): i + 1]
        std = statistics.stdev(window) if len(window) > 1 else 0
        upper.append(mid[i] + std_dev * std)
        lower.append(mid[i] - std_dev * std)
    return upper, mid, lower


def true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[Optional[float]]:
    if len(closes) < 2:
        return [None] * len(closes)
    tr_values = [true_range(highs[i], lows[i], closes[i - 1]) for i in range(1, len(closes))]
    atr_vals: list[Optional[float]] = [None] * len(closes)
    start = period
    if len(tr_values) >= period:
        atr_vals[start] = sum(tr_values[:period]) / period
        for i in range(period, len(tr_values)):
            atr_vals[i + 1] = (atr_vals[i] * (period - 1) + tr_values[i]) / period
    return atr_vals


def adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[Optional[float]]:
    n = len(closes)
    if n < period + 1:
        return [None] * n
    tr_vals: list[Optional[float]] = [None] * n
    plus_dm: list[Optional[float]] = [None] * n
    minus_dm: list[Optional[float]] = [None] * n
    for i in range(1, n):
        tr_vals[i] = true_range(highs[i], lows[i], closes[i - 1])
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move
        else:
            plus_dm[i] = 0.0
        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move
        else:
            minus_dm[i] = 0.0
    avg_tr: list[Optional[float]] = [None] * n
    avg_plus: list[Optional[float]] = [None] * n
    avg_minus: list[Optional[float]] = [None] * n
    valid = [v for v in tr_vals if v is not None]
    if len(valid) >= period:
        idx = period
        avg_tr[idx] = sum(valid[:period]) / period
        avg_plus[idx] = sum(v for v in plus_dm[1:period + 1] if v is not None) / period
        avg_minus[idx] = sum(v for v in minus_dm[1:period + 1] if v is not None) / period
        for i in range(period + 1, n):
            prev_tr = avg_tr[i - 1] or 0
            prev_p = avg_plus[i - 1] or 0
            prev_m = avg_minus[i - 1] or 0
            avg_tr[i] = (prev_tr * (period - 1) + (tr_vals[i] or 0)) / period
            avg_plus[i] = (prev_p * (period - 1) + (plus_dm[i] or 0)) / period
            avg_minus[i] = (prev_m * (period - 1) + (minus_dm[i] or 0)) / period
    adx_vals: list[Optional[float]] = [None] * n
    for i in range(period, n):
        pdi = (avg_plus[i] / avg_tr[i] * 100) if avg_tr[i] and avg_tr[i] > 0 else 0
        mdi = (avg_minus[i] / avg_tr[i] * 100) if avg_tr[i] and avg_tr[i] > 0 else 0
        dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0
        if i == period:
            adx_vals[i] = dx
        else:
            prev = adx_vals[i - 1] or dx
            adx_vals[i] = (prev * (period - 1) + dx) / period
    return adx_vals


def volatility(data: list[float], period: int = 20) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * (period - 1)
    for i in range(period - 1, len(data)):
        window = data[i - period + 1: i + 1]
        returns = [(window[j] - window[j - 1]) / window[j - 1] for j in range(1, len(window))]
        result.append(statistics.stdev(returns) if len(returns) > 1 else 0)
    return result


def z_score(data: list[float], period: int = 20) -> list[Optional[float]]:
    result: list[Optional[float]] = []
    for i in range(len(data)):
        if i < period - 1:
            result.append(None)
        else:
            window = data[i - period + 1: i + 1]
            mean = sum(window) / len(window)
            std = statistics.stdev(window) if len(window) > 1 else 1
            result.append((data[i] - mean) / std)
    return result


def heikin_ashi(opens: list[float], highs: list[float], lows: list[float], closes: list[float]):
    n = len(closes)
    ha_open: list[float] = [0.0] * n
    ha_close: list[float] = [0.0] * n
    ha_high: list[float] = [0.0] * n
    ha_low: list[float] = [0.0] * n
    if n == 0:
        return ha_open, ha_high, ha_low, ha_close
    ha_close[0] = (opens[0] + highs[0] + lows[0] + closes[0]) / 4
    ha_open[0] = opens[0]
    ha_high[0] = highs[0]
    ha_low[0] = lows[0]
    for i in range(1, n):
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2
        ha_close[i] = (opens[i] + highs[i] + lows[i] + closes[i]) / 4
        ha_high[i] = max(highs[i], ha_open[i], ha_close[i])
        ha_low[i] = min(lows[i], ha_open[i], ha_close[i])
    return ha_open, ha_high, ha_low, ha_close


def detect_divergence(
    price: list[float], indicator: list[Optional[float]], lookback: int = 20
) -> str:
    recent_price = price[-lookback:]
    recent_ind = [i for i in indicator[-lookback:] if i is not None]
    if len(recent_ind) < 10:
        return "none"
    n = len(recent_price)
    price_peaks, price_troughs = [], []
    ind_peaks, ind_troughs = [], []
    for i in range(2, n - 2):
        if recent_price[i] > recent_price[i - 1] and recent_price[i] > recent_price[i - 2] and recent_price[i] > recent_price[i + 1] and recent_price[i] > recent_price[i + 2]:
            price_peaks.append((i, recent_price[i]))
        if recent_price[i] < recent_price[i - 1] and recent_price[i] < recent_price[i - 2] and recent_price[i] < recent_price[i + 1] and recent_price[i] < recent_price[i + 2]:
            price_troughs.append((i, recent_price[i]))
    ind_trunc = indicator[-(lookback + 2):]
    for idx in range(2, len(ind_trunc) - 2):
        val = ind_trunc[idx]
        if val is None:
            continue
        prev, prev2 = ind_trunc[idx - 1], ind_trunc[idx - 2]
        nxt, nxt2 = ind_trunc[idx + 1], ind_trunc[idx + 2]
        if prev is None or prev2 is None or nxt is None or nxt2 is None:
            continue
        if val > prev and val > prev2 and val > nxt and val > nxt2:
            offset = len(ind_trunc) - idx
            real_idx = n - offset
            ind_peaks.append((real_idx, val))
        if val < prev and val < prev2 and val < nxt and val < nxt2:
            offset = len(ind_trunc) - idx
            real_idx = n - offset
            ind_troughs.append((real_idx, val))
    if len(price_peaks) >= 2 and len(ind_peaks) >= 2:
        last_pp = price_peaks[-1][1]
        prev_pp = price_peaks[-2][1]
        last_ip = ind_peaks[-1][1]
        prev_ip = ind_peaks[-2][1]
        if last_pp > prev_pp and last_ip < prev_ip:
            return "bearish"
    if len(price_troughs) >= 2 and len(ind_troughs) >= 2:
        last_pt = price_troughs[-1][1]
        prev_pt = price_troughs[-2][1]
        last_it = ind_troughs[-1][1]
        prev_it = ind_troughs[-2][1]
        if last_pt < prev_pt and last_it > prev_it:
            return "bullish"
    return "none"


def vwap(highs: list[float], lows: list[float], closes: list[float], volumes: list[float]) -> list[Optional[float]]:
    result: list[Optional[float]] = []
    cum_pv = 0.0
    cum_vol = 0.0
    for i in range(len(closes)):
        typical_price = (highs[i] + lows[i] + closes[i]) / 3
        cum_pv += typical_price * volumes[i]
        cum_vol += volumes[i]
        result.append(cum_pv / cum_vol if cum_vol > 0 else None)
    return result

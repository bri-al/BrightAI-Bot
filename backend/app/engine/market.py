import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import httpx
from app.config import settings


DATA_DIR = Path(__file__).parent.parent.parent / "market_data"
BINANCE_API = "https://api.binance.com/api/v3"
YAHOO_API = "https://query1.finance.yahoo.com/v8/finance/chart"
CRYPTO_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
FOREX_SYMBOLS = {"EURUSD", "GBPUSD", "USDJPY", "XAUUSD"}
STOCK_SYMBOLS = {"AAPL", "MSFT", "GOOGL"}

YAHOO_MAP = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "XAUUSD": "XAUUSD=X",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "GOOGL": "GOOGL",
}


class MarketDataProvider:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._http = httpx.AsyncClient(timeout=15)

    async def close(self):
        await self._http.aclose()

    def _file_path(self, symbol: str, timeframe: str = "1h") -> Path:
        return DATA_DIR / f"{symbol}_{timeframe}.json"

    async def fetch_historical(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> list[dict]:
        if settings.broker == "mt5":
            fetched = await self._fetch_mt5_rates(symbol, timeframe, max(limit, 200))
            if fetched:
                if limit >= 200:
                    self._save(symbol, timeframe, fetched)
                return fetched[-limit:] if len(fetched) > limit else fetched

        candles = self._load(symbol, timeframe)
        if len(candles) >= limit:
            return candles[-limit:]

        if symbol in CRYPTO_SYMBOLS:
            fetched = await self._fetch_binance_klines(symbol, timeframe, limit)
            if fetched:
                self._save(symbol, timeframe, fetched)
                return fetched[-limit:] if len(fetched) > limit else fetched

        if symbol in FOREX_SYMBOLS or symbol in STOCK_SYMBOLS:
            fetched = await self._fetch_yahoo_ohlcv(symbol, timeframe, limit)
            if fetched:
                self._save(symbol, timeframe, fetched)
                return fetched[-limit:] if len(fetched) > limit else fetched

        if not candles:
            candles = self.generate_synthetic(symbol, days=365)
        return candles[-limit:] if len(candles) > limit else candles

    async def _fetch_mt5_rates(self, symbol: str, timeframe: str, limit: int) -> list[dict]:
        import MetaTrader5 as mt5
        if not mt5.initialize(
            path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
            server=settings.mt5_server,
            login=settings.mt5_login,
            password=settings.mt5_password,
            timeout=15000,
        ):
            return []
        tf_map = {
            "5m": mt5.TIMEFRAME_M5,
            "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30,
            "1h": mt5.TIMEFRAME_H1,
            "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1,
        }
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
        from app.execution.mt5 import _map_symbol
        mt5_symbol = _map_symbol(symbol)
        mt5.symbol_select(mt5_symbol, True)
        try:
            rates = mt5.copy_rates_from_pos(mt5_symbol, mt5_tf, 0, limit)
            if rates is None or len(rates) == 0:
                return []
            return [
                {
                    "timestamp": datetime.fromtimestamp(r[0], tz=timezone.utc).isoformat(),
                    "open": round(float(r[1]), 6),
                    "high": round(float(r[2]), 6),
                    "low": round(float(r[3]), 6),
                    "close": round(float(r[4]), 6),
                    "volume": float(r[5]),
                }
                for r in rates
            ]
        except Exception:
            return []

    async def _fetch_binance_klines(self, symbol: str, timeframe: str, limit: int) -> list[dict]:
        interval_map = {"5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d"}
        interval = interval_map.get(timeframe, "1h")
        try:
            resp = await self._http.get(
                f"{BINANCE_API}/klines",
                params={"symbol": symbol, "interval": interval, "limit": min(limit, 1000)},
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "timestamp": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc).isoformat(),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in data
            ]
        except Exception:
            return []

    async def _fetch_yahoo_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[dict]:
        yahoo_symbol = YAHOO_MAP.get(symbol)
        if not yahoo_symbol:
            return []
        interval_map = {"5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d"}
        interval = interval_map.get(timeframe, "1h")
        range_map = {500: "1mo", 100: "5d", 200: "1mo", 1000: "3mo"}
        rng = "1mo"
        for lim, r in sorted(range_map.items()):
            if limit <= lim:
                rng = r
                break
        try:
            resp = await self._http.get(
                f"{YAHOO_API}/{yahoo_symbol}",
                params={"interval": interval, "range": rng},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            result = data.get("chart", {}).get("result", [])
            if not result:
                return []
            timestamps = result[0].get("timestamp", [])
            quotes = result[0].get("indicators", {}).get("quote", [{}])[0]
            ohlcv = []
            for i, ts in enumerate(timestamps):
                o = quotes.get("open", [None])[i]
                h = quotes.get("high", [None])[i]
                l = quotes.get("low", [None])[i]
                c = quotes.get("close", [None])[i]
                v = quotes.get("volume", [None])[i]
                if o is not None and c is not None:
                    ohlcv.append({
                        "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                        "open": round(float(o), 2),
                        "high": round(float(h), 2) if h else round(float(o), 2),
                        "low": round(float(l), 2) if l else round(float(o), 2),
                        "close": round(float(c), 2),
                        "volume": float(v) if v else 0,
                    })
            return ohlcv
        except Exception:
            return []

    async def fetch_latest(self, symbol: str, timeframe: str = "1h") -> Optional[dict]:
        candles = await self.fetch_historical(symbol, timeframe, limit=1)
        return candles[-1] if candles else None

    def fetch_realtime(self, symbol: str) -> dict:
        candles = self._load(symbol, "1h")
        if not candles:
            base = self._base_price(symbol)
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "open": base, "high": base, "low": base, "close": base, "volume": 0,
            }
        last = candles[-1]
        price = last["close"]
        ret = random.gauss(0, 0.002)
        new_price = price * (1 + ret)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "open": round(price, 2),
            "high": round(max(price, new_price) * (1 + abs(random.gauss(0, 0.001))), 2),
            "low": round(min(price, new_price) * (1 - abs(random.gauss(0, 0.001))), 2),
            "close": round(new_price, 2),
            "volume": round(random.uniform(100, 10000), 2),
        }

    def generate_synthetic(self, symbol: str, days: int = 365, base_price: Optional[float] = None) -> list[dict]:
        if base_price is None:
            base_price = self._base_price(symbol)
        candles = []
        price = base_price
        now = datetime.now(timezone.utc)
        for i in range(days * 24):
            ts = (now - timedelta(hours=days * 24 - i)).isoformat()
            ret = random.gauss(0.0001, 0.02)
            price *= 1 + ret
            candles.append({
                "timestamp": ts,
                "open": round(price * (1 - 0.006), 2),
                "high": round(price * (1 + abs(random.gauss(0, 0.01))), 2),
                "low": round(price * (1 - abs(random.gauss(0, 0.01))), 2),
                "close": round(price, 2),
                "volume": round(random.uniform(100, 10000), 2),
            })
        self._save(symbol, "1h", candles)
        return candles

    def _base_price(self, symbol: str) -> float:
        prices = {
            "BTCUSDT": 65000, "ETHUSDT": 3500, "SOLUSDT": 140,
            "EURUSD": 1.08, "GBPUSD": 1.27, "USDJPY": 150, "XAUUSD": 2350,
            "AAPL": 190, "MSFT": 420, "GOOGL": 175,
        }
        return prices.get(symbol, 100.0)

    def _load(self, symbol: str, timeframe: str) -> list[dict]:
        path = self._file_path(symbol, timeframe)
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _save(self, symbol: str, timeframe: str, candles: list[dict]):
        path = self._file_path(symbol, timeframe)
        with open(path, "w") as f:
            json.dump(candles, f, indent=2)


market_data = MarketDataProvider()

import hashlib
import hmac
import time
import uuid
from typing import Optional
import httpx
from app.execution.base import BaseExecutor, OrderResult
from app.config import settings


class BinanceExecutor(BaseExecutor):
    def __init__(self):
        self.base_url = "https://testnet.binance.vision/api/v3" if settings.binance_testnet else "https://api.binance.com/api/v3"
        self.api_key = settings.binance_api_key
        self.secret_key = settings.binance_secret_key

    def _sign(self, params: dict) -> dict:
        params["recvWindow"] = 5000
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        signature = hmac.new(
            self.secret_key.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    async def _request(self, method: str, path: str, params: dict = None) -> dict:
        headers = {"X-MBX-APIKEY": self.api_key}
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            if params:
                params = self._sign(params)
            resp = await client.request(method, path, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def market_order(self, symbol: str, side: str, size: float, sl: float = 0.0, tp: float = 0.0) -> OrderResult:
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": size,
            "timestamp": int(time.time() * 1000),
        }
        try:
            data = await self._request("POST", "/order", params)
            fills = data.get("fills", [{}])
            avg_price = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills) / max(sum(float(f.get("qty", 0)) for f in fills), 1)
            return OrderResult(
                success=True,
                order_id=data.get("orderId", str(uuid.uuid4())),
                filled_price=avg_price or float(data.get("cummulativeQuoteQty", 0)) / max(float(data.get("executedQty", 1)), 1),
                filled_size=float(data.get("executedQty", size)),
                message=f"Binance {side} {symbol} filled",
            )
        except Exception as e:
            return OrderResult(success=False, message=str(e))

    async def limit_order(self, symbol: str, side: str, size: float, price: float) -> OrderResult:
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": size,
            "price": price,
            "timestamp": int(time.time() * 1000),
        }
        try:
            data = await self._request("POST", "/order", params)
            return OrderResult(success=True, order_id=data.get("orderId", ""), filled_price=price, filled_size=size)
        except Exception as e:
            return OrderResult(success=False, message=str(e))

    async def stop_loss_order(self, symbol: str, side: str, size: float, stop_price: float) -> OrderResult:
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "STOP_LOSS_LIMIT",
            "timeInForce": "GTC",
            "quantity": size,
            "price": stop_price,
            "stopPrice": stop_price,
            "timestamp": int(time.time() * 1000),
        }
        try:
            data = await self._request("POST", "/order", params)
            return OrderResult(success=True, order_id=data.get("orderId", ""))
        except Exception as e:
            return OrderResult(success=False, message=str(e))

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._request("DELETE", "/order", {"orderId": order_id, "timestamp": int(time.time() * 1000)})
            return True
        except Exception:
            return False

    async def get_position(self, symbol: str) -> Optional[dict]:
        try:
            data = await self._request("GET", "/account", {"timestamp": int(time.time() * 1000)})
            for bal in data.get("balances", []):
                if bal["asset"] == symbol.replace("USDT", ""):
                    free = float(bal["free"])
                    locked = float(bal["locked"])
                    if free + locked > 0:
                        return {"symbol": symbol, "size": free + locked, "free": free}
            return None
        except Exception:
            return None

    async def get_account(self) -> dict:
        try:
            data = await self._request("GET", "/account", {"timestamp": int(time.time() * 1000)})
            balances = {b["asset"]: float(b["free"]) + float(b["locked"]) for b in data.get("balances", [])}
            return {"balance": balances.get("USDT", 0), "equity": balances.get("USDT", 0)}
        except Exception:
            return {"balance": 0, "equity": 0}

    async def get_price(self, symbol: str) -> float:
        try:
            data = await self._request("GET", "/ticker/price", {"symbol": symbol})
            return float(data.get("price", 0))
        except Exception:
            return 0.0

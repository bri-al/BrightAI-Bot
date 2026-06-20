from typing import Optional
import httpx
from app.execution.base import BaseExecutor, OrderResult
from app.config import settings


class AlpacaExecutor(BaseExecutor):
    def __init__(self):
        base = "https://paper-api.alpaca.markets/v2" if settings.alpaca_paper else "https://api.alpaca.markets/v2"
        self.base_url = base
        self.headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
        }

    async def _request(self, method: str, path: str, json_data: dict = None) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            resp = await client.request(method, path, headers=self.headers, json=json_data)
            resp.raise_for_status()
            if resp.content:
                return resp.json()
            return {}

    async def market_order(self, symbol: str, side: str, size: float, sl: float = 0.0, tp: float = 0.0) -> OrderResult:
        data = {
            "symbol": symbol,
            "qty": size,
            "side": side,
            "type": "market",
            "time_in_force": "gtc",
        }
        try:
            resp = await self._request("POST", "/orders", data)
            return OrderResult(
                success=True,
                order_id=resp.get("id", ""),
                filled_price=float(resp.get("filled_avg_price", 0)),
                filled_size=float(resp.get("filled_qty", size)),
                message=f"Alpaca {side} {symbol}",
            )
        except Exception as e:
            return OrderResult(success=False, message=str(e))

    async def limit_order(self, symbol: str, side: str, size: float, price: float) -> OrderResult:
        data = {
            "symbol": symbol,
            "qty": size,
            "side": side,
            "type": "limit",
            "limit_price": price,
            "time_in_force": "gtc",
        }
        try:
            resp = await self._request("POST", "/orders", data)
            return OrderResult(success=True, order_id=resp.get("id", ""))
        except Exception as e:
            return OrderResult(success=False, message=str(e))

    async def stop_loss_order(self, symbol: str, side: str, size: float, stop_price: float) -> OrderResult:
        data = {
            "symbol": symbol,
            "qty": size,
            "side": side,
            "type": "stop",
            "stop_price": stop_price,
            "time_in_force": "gtc",
        }
        try:
            resp = await self._request("POST", "/orders", data)
            return OrderResult(success=True, order_id=resp.get("id", ""))
        except Exception as e:
            return OrderResult(success=False, message=str(e))

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._request("DELETE", f"/orders/{order_id}")
            return True
        except Exception:
            return False

    async def get_position(self, symbol: str) -> Optional[dict]:
        try:
            resp = await self._request("GET", f"/positions/{symbol}")
            return {"symbol": symbol, "size": float(resp.get("qty", 0)), "entry": float(resp.get("avg_entry_price", 0))}
        except Exception:
            return None

    async def get_account(self) -> dict:
        try:
            resp = await self._request("GET", "/account")
            return {
                "balance": float(resp.get("cash", 0)),
                "equity": float(resp.get("equity", 0)),
                "buying_power": float(resp.get("buying_power", 0)),
            }
        except Exception:
            return {"balance": 0, "equity": 0}

    async def get_price(self, symbol: str) -> float:
        try:
            resp = await self._request("GET", f"/stocks/{symbol}/trades/latest")
            return float(resp.get("trade", {}).get("p", 0))
        except Exception:
            return 0.0

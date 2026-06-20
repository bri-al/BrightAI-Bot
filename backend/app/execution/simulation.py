import random
import uuid
from typing import Optional
from app.execution.base import BaseExecutor, OrderResult
from app.config import settings


class SimulationExecutor(BaseExecutor):
    def __init__(self):
        self.positions: dict[str, dict] = {}
        self.orders: dict[str, dict] = {}

    async def market_order(self, symbol: str, side: str, size: float, sl: float = 0.0, tp: float = 0.0) -> OrderResult:
        price = await self.get_price(symbol)
        slippage = price * settings.default_slippage * random.uniform(0.5, 1.5)
        filled_price = price + slippage if side == "buy" else price - slippage
        order_id = f"sim_{uuid.uuid4().hex[:12]}"
        self.positions[symbol] = {
            "symbol": symbol,
            "side": side,
            "size": size,
            "entry_price": filled_price,
            "order_id": order_id,
        }
        return OrderResult(
            success=True,
            order_id=order_id,
            filled_price=filled_price,
            filled_size=size,
            message=f"Simulated {side} {size:.4f} {symbol} @ {filled_price:.2f}",
        )

    async def limit_order(self, symbol: str, side: str, size: float, price: float) -> OrderResult:
        order_id = f"sim_{uuid.uuid4().hex[:12]}"
        self.orders[order_id] = {
            "symbol": symbol, "side": side, "size": size, "price": price, "status": "open"
        }
        return OrderResult(success=True, order_id=order_id, filled_price=price, filled_size=size)

    async def stop_loss_order(self, symbol: str, side: str, size: float, stop_price: float) -> OrderResult:
        return await self.market_order(symbol, side, size)

    async def cancel_order(self, order_id: str) -> bool:
        return self.orders.pop(order_id, None) is not None

    async def get_position(self, symbol: str) -> Optional[dict]:
        return self.positions.get(symbol)

    async def get_account(self) -> dict:
        return {
            "balance": settings.initial_capital,
            "equity": settings.initial_capital,
            "margin": 0,
        }

    async def get_price(self, symbol: str) -> float:
        from app.engine.market import market_data
        candle = await market_data.fetch_latest(symbol)
        if candle:
            return candle["close"]
        prices = {
            "BTCUSDT": 65000, "ETHUSDT": 3500, "SOLUSDT": 140,
            "EURUSD": 1.08, "GBPUSD": 1.27, "USDJPY": 150,
            "AAPL": 190, "MSFT": 420, "GOOGL": 175,
        }
        return prices.get(symbol, 100.0)

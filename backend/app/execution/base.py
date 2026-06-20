from abc import ABC, abstractmethod
from typing import Optional


class OrderResult:
    def __init__(
        self,
        success: bool,
        order_id: str = "",
        filled_price: float = 0.0,
        filled_size: float = 0.0,
        message: str = "",
    ):
        self.success = success
        self.order_id = order_id
        self.filled_price = filled_price
        self.filled_size = filled_size
        self.message = message

    def __repr__(self):
        status = "OK" if self.success else "FAIL"
        return f"<OrderResult {status} id={self.order_id} price={self.filled_price} size={self.filled_size} msg={self.message!r}>"


class BaseExecutor(ABC):
    @property
    def broker_name(self) -> str:
        return type(self).__name__.replace("Executor", "")

    @property
    def connected(self) -> bool:
        return True

    @abstractmethod
    async def market_order(self, symbol: str, side: str, size: float, sl: float = 0.0, tp: float = 0.0) -> OrderResult:
        ...

    @abstractmethod
    async def limit_order(self, symbol: str, side: str, size: float, price: float) -> OrderResult:
        ...

    @abstractmethod
    async def stop_loss_order(self, symbol: str, side: str, size: float, stop_price: float) -> OrderResult:
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        ...

    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[dict]:
        ...

    @abstractmethod
    async def get_account(self) -> dict:
        ...

    @abstractmethod
    async def get_price(self, symbol: str) -> float:
        ...

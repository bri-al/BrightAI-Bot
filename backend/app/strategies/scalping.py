from app.strategies.base import BaseStrategy
from app.engine.signals import _scalping_signal


class ScalpingStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("scalping")
        self.parameters = {
            "rsi_period": 7,
            "macd_fast": 6,
            "macd_slow": 13,
            "macd_signal": 5,
        }

    async def generate_signal(self, candles: list[dict], symbols: list[str]) -> dict:
        return _scalping_signal(candles)

    def get_market_preference(self) -> str:
        return "volatile"

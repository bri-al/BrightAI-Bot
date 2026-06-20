from app.strategies.base import BaseStrategy
from app.engine.signals import _momentum_signal


class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("momentum")
        self.parameters = {
            "fast_ema": 12,
            "slow_ema": 26,
            "rsi_period": 14,
            "confidence_threshold": 50,
        }

    async def generate_signal(self, candles: list[dict], symbols: list[str]) -> dict:
        return _momentum_signal(candles)

    def get_market_preference(self) -> str:
        return "trend"

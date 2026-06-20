from app.strategies.base import BaseStrategy
from app.engine.signals import _mean_reversion_signal


class MeanReversionStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("mean_reversion")
        self.parameters = {
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70,
            "bb_period": 20,
            "bb_std": 2.0,
        }

    async def generate_signal(self, candles: list[dict], symbols: list[str]) -> dict:
        return _mean_reversion_signal(candles)

    def get_market_preference(self) -> str:
        return "range"

from abc import ABC, abstractmethod
from typing import Optional


class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name
        self.parameters: dict = {}

    @abstractmethod
    async def generate_signal(self, candles: list[dict], symbols: list[str]) -> dict:
        ...

    @abstractmethod
    def get_market_preference(self) -> str:
        ...


class StrategyManager:
    def __init__(self):
        self._strategies: dict[str, BaseStrategy] = {}

    def register(self, strategy: BaseStrategy):
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> Optional[BaseStrategy]:
        return self._strategies.get(name)

    def list(self) -> dict[str, BaseStrategy]:
        return dict(self._strategies)

    def select_for_regime(self, regime: str) -> Optional[BaseStrategy]:
        preference_map = {
            "strong_trend": "momentum",
            "trend": "momentum",
            "weak_trend": "momentum",
            "range": "mean_reversion",
            "neutral": "momentum",
            "volatile": "scalping",
            "choppy": "scalping",
        }
        preferred = preference_map.get(regime, "momentum")
        return self._strategies.get(preferred)


strategy_manager = StrategyManager()

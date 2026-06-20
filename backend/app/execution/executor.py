from app.config import settings
from app.execution.base import BaseExecutor
from app.execution.simulation import SimulationExecutor

_executor: BaseExecutor = None


def get_executor() -> BaseExecutor:
    global _executor
    if _executor is not None:
        return _executor

    broker = settings.broker
    if broker == "binance":
        from app.execution.binance import BinanceExecutor
        _executor = BinanceExecutor()
    elif broker == "alpaca":
        from app.execution.alpaca import AlpacaExecutor
        _executor = AlpacaExecutor()
    elif broker == "mt5":
        from app.execution.mt5 import MT5Executor
        _executor = MT5Executor()
    else:
        _executor = SimulationExecutor()

    return _executor

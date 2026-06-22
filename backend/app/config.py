import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    app_name: str = "AI Trading Platform"
    version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{Path(__file__).parent.parent / 'trading.db'}",
    )

    # Auth
    api_key: str = os.getenv("API_KEY", "")
    api_key_name: str = "X-API-Key"

    # Capital & Risk
    initial_capital: float = float(os.getenv("INITIAL_CAPITAL", "1000.0"))
    max_risk_per_trade: float = float(os.getenv("MAX_RISK_PER_TRADE", "0.02"))
    max_daily_loss: float = float(os.getenv("MAX_DAILY_LOSS", "0.05"))
    max_drawdown: float = float(os.getenv("MAX_DRAWDOWN", "0.15"))
    max_open_positions: int = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
    min_rr_ratio: float = float(os.getenv("MIN_RR_RATIO", "1.5"))
    default_slippage: float = float(os.getenv("DEFAULT_SLIPPAGE", "0.001"))
    min_confidence: int = int(os.getenv("MIN_CONFIDENCE", "30"))
    min_position_value: float = float(os.getenv("MIN_POSITION_VALUE", "1.0"))
    min_trading_equity: float = float(os.getenv("MIN_TRADING_EQUITY", "10.0"))
    max_position_size_pct: float = float(os.getenv("MAX_POSITION_SIZE_PCT", "0.02"))

    # Trading config
    default_timeframe: str = os.getenv("DEFAULT_TIMEFRAME", "5m")
    scan_interval_seconds: int = int(os.getenv("SCAN_INTERVAL", "60"))
    strategy: Literal["momentum", "mean_reversion", "scalping", "adaptive"] = os.getenv(
        "STRATEGY", "adaptive"
    )

    # Per-symbol strategy mapping (overrides `strategy` for specific symbols)
    # Based on 5m backtest (30 days, $100):
    #   BTCUSDT -> momentum_tf (+68.91%, DD=13.2%) — momentum with 1h trend filter
    #   EURUSD  -> adaptive      (+52.87%, DD=18.7%) — regime-gated momentum/meanrev/scalp
    #   GBPUSD  -> momentum_tf   (+28.22%, DD=19.2%) — momentum with 1h trend filter
    #   XAUUSD  -> momentum      (+84.40%, DD=16.9%) — pure momentum confluence
    per_symbol_strategy: dict = field(default_factory=lambda: {
        "BTCUSDT": "momentum_tf",
        "EURUSD": "adaptive",
        "GBPUSD": "momentum_tf",
        "XAUUSD": "momentum",
    })

    # Broker selection
    broker: Literal["binance", "mt5", "alpaca", "simulation"] = os.getenv(
        "BROKER", "simulation"
    )

    # Binance
    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_secret_key: str = os.getenv("BINANCE_SECRET_KEY", "")
    binance_testnet: bool = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

    # Alpaca
    alpaca_api_key: str = os.getenv("ALPACA_API_KEY", "")
    alpaca_secret_key: str = os.getenv("ALPACA_SECRET_KEY", "")
    alpaca_paper: bool = os.getenv("ALPACA_PAPER", "true").lower() == "true"

    # MT5
    mt5_server: str = os.getenv("MT5_SERVER", "")
    mt5_login: int = int(os.getenv("MT5_LOGIN", "0"))
    mt5_password: str = os.getenv("MT5_PASSWORD", "")

    # Symbols
    crypto_symbols: list = field(default_factory=lambda: ["BTCUSDT"])
    forex_symbols: list = field(default_factory=lambda: ["EURUSD", "GBPUSD", "XAUUSD"])
    stock_symbols: list = field(default_factory=lambda: [])

    @property
    def all_symbols(self) -> list[str]:
        return self.crypto_symbols + self.forex_symbols + self.stock_symbols

    def get_strategy(self, symbol: str) -> str:
        return self.per_symbol_strategy.get(symbol, self.strategy)

    @property
    def database_dir(self) -> Path:
        return Path(__file__).parent.parent


settings = Settings()

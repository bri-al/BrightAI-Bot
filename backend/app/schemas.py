from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TradeCreate(BaseModel):
    symbol: str
    direction: str
    entry_price: float
    size: float
    stop_loss: float
    take_profit: Optional[float] = None
    strategy: Optional[str] = None


class TradeResponse(BaseModel):
    id: int
    symbol: str
    asset_class: str
    direction: str
    entry_price: float
    exit_price: Optional[float] = None
    size: float
    stop_loss: float
    take_profit: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    status: str
    strategy: Optional[str] = None
    signal_reason: Optional[str] = None
    exit_reason: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PortfolioResponse(BaseModel):
    balance: float
    equity: float
    peak_equity: float
    drawdown: float
    open_positions: int
    daily_trades: int
    daily_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    is_trading: bool


class StrategyUpdate(BaseModel):
    strategy: Optional[str] = Field(None, pattern="^(momentum|mean_reversion|scalping|adaptive)$")
    per_symbol_strategy: Optional[dict[str, str]] = None
    risk_per_trade: Optional[float] = Field(None, ge=0.001, le=0.1)
    max_open_positions: Optional[int] = Field(None, ge=1, le=20)


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    strategy: str = "adaptive"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000.0
    days: int = 365


class BacktestTrade(BaseModel):
    entry_idx: int
    exit_idx: int
    type: str
    entry: float
    exit: float
    pnl: float
    pnl_pct: float


class BacktestResponse(BaseModel):
    strategy: str
    symbol: str
    total_return: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    num_trades: int
    sharpe_ratio: float
    trades: list[BacktestTrade] = []


class SignalResponse(BaseModel):
    symbol: str
    action: str
    confidence: float
    price: float
    regime: str
    reason: str
    timestamp: datetime


class BotControl(BaseModel):
    action: str = Field(..., pattern="^(start|stop|pause|resume)$")


class WSMessage(BaseModel):
    type: str
    data: dict

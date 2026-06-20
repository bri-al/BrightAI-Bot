from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from app.database import Base


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Trade(BaseModel):
    __tablename__ = "trades"

    symbol = Column(String(20), nullable=False, index=True)
    asset_class = Column(String(10), nullable=False)
    direction = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    size = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    status = Column(String(20), default="open")
    strategy = Column(String(50), nullable=True)
    signal_reason = Column(Text, nullable=True)
    exit_reason = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    slippage = Column(Float, nullable=True)
    commission = Column(Float, nullable=True)
    broker_order_id = Column(String(100), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class Account(BaseModel):
    __tablename__ = "accounts"

    broker = Column(String(20), nullable=False)
    balance = Column(Float, nullable=False, default=0.0)
    equity = Column(Float, nullable=False, default=0.0)
    peak_equity = Column(Float, nullable=False, default=0.0)
    drawdown = Column(Float, nullable=False, default=0.0)
    open_positions = Column(Integer, default=0)
    daily_trades = Column(Integer, default=0)
    daily_pnl = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    is_trading = Column(Boolean, default=False)
    last_reset_date = Column(String(10), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class StrategyLog(BaseModel):
    __tablename__ = "strategy_logs"

    strategy = Column(String(50), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    signal = Column(String(10), nullable=True)
    confidence = Column(Float, nullable=True)
    regime = Column(String(20), nullable=True)
    price = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    executed = Column(Boolean, default=False)
    metadata_json = Column(JSON, nullable=True)


class PerformanceSnapshot(BaseModel):
    __tablename__ = "performance_snapshots"

    balance = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    drawdown = Column(Float, nullable=False)
    daily_pnl = Column(Float, nullable=False)
    open_positions = Column(Integer, default=0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)

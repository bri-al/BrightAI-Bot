from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Trade, Account, PerformanceSnapshot
from app.schemas import PortfolioResponse
from app.risk.manager import risk_engine
from app.execution.executor import get_executor
from app.config import settings
from app.auth import verify_api_key

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("")
async def get_portfolio(db: AsyncSession = Depends(get_db)):
    state = risk_engine.to_dict()

    try:
        exec = get_executor()
        broker_account = await exec.get_account()
        if broker_account.get("balance", 0) > 0:
            broker_balance = broker_account["balance"]
            broker_equity = broker_account.get("equity", broker_balance)
            state["balance"] = broker_balance
            state["equity"] = broker_equity
            risk_engine.current_equity = broker_equity
            if broker_equity > risk_engine.peak_equity or risk_engine.peak_equity == settings.initial_capital:
                risk_engine.peak_equity = max(broker_equity, broker_balance)
            state["drawdown"] = round(
                (risk_engine.peak_equity - broker_equity) / max(risk_engine.peak_equity, 1) * 100, 2
            )
    except Exception:
        pass

    total_wins = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "closed", Trade.pnl > 0)
    ) or 0
    total_losses = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "closed", Trade.pnl <= 0)
    ) or 0
    total_trades = await db.scalar(
        select(func.count(Trade.id))
    ) or 0

    result = await db.execute(
        select(Trade).where(Trade.status == "open").order_by(Trade.created_at.desc())
    )
    open_positions = result.scalars().all()

    return {
        **state,
        "total_trades": total_trades,
        "winning_trades": total_wins,
        "losing_trades": total_losses,
        "open_positions_detail": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "direction": t.direction,
                "entry": t.entry_price,
                "size": t.size,
                "sl": t.stop_loss,
                "tp": t.take_profit,
                "strategy": t.strategy,
                "pnl": t.pnl,
            }
            for t in open_positions
        ],
    }

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import Trade
from app.schemas import TradeResponse
from app.risk.manager import risk_engine
from app.execution.executor import get_executor
from app.engine.market import market_data
from app.auth import verify_api_key

router = APIRouter(prefix="/trades", tags=["Trades"])


@router.get("")
async def get_trades(status: str = None, db: AsyncSession = Depends(get_db)):
    query = select(Trade).order_by(desc(Trade.created_at)).limit(100)
    if status and status != "all":
        query = query.where(Trade.status == status)
    result = await db.execute(query)
    trades = result.scalars().all()
    return [TradeResponse.model_validate(t) for t in trades]


@router.get("/open")
async def get_open_trades(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Trade).where(Trade.status == "open").order_by(desc(Trade.created_at))
    )
    trades = result.scalars().all()
    return [TradeResponse.model_validate(t) for t in trades]


@router.get("/closed")
async def get_closed_trades(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Trade).where(Trade.status == "closed").order_by(desc(Trade.created_at)).limit(100)
    )
    trades = result.scalars().all()
    return [TradeResponse.model_validate(t) for t in trades]


@router.get("/{trade_id}")
async def get_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    trade = await db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(404, "Trade not found")
    return TradeResponse.model_validate(trade)


@router.post("/{trade_id}/close")
async def close_trade(trade_id: int, db: AsyncSession = Depends(get_db), auth: str = Depends(verify_api_key)):
    trade = await db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(404, "Trade not found")
    if trade.status == "closed":
        raise HTTPException(400, "Trade already closed")

    executor = get_executor()
    price = await executor.get_price(trade.symbol)
    if not price:
        price = trade.entry_price

    side = "sell" if trade.direction == "long" else "buy"
    order = await executor.market_order(trade.symbol, side, trade.size)

    trade.exit_price = price
    result = risk_engine.close_trade(trade.symbol, price)
    pnl = result["pnl"] if result else 0.0
    trade.pnl = round(pnl, 2)
    trade.pnl_pct = round(pnl / (trade.entry_price * trade.size) * 100 if trade.entry_price * trade.size > 0 else 0, 2)
    trade.status = "closed"
    trade.exit_reason = "manual_close"

    await db.commit()
    await db.refresh(trade)
    return TradeResponse.model_validate(trade)

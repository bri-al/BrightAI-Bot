from fastapi import APIRouter, Depends
from app.schemas import StrategyUpdate
from app.strategies.base import strategy_manager
from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.scalping import ScalpingStrategy
from app.config import settings
from app.auth import verify_api_key

router = APIRouter(prefix="/strategy", tags=["Strategies"])

strategy_manager.register(MomentumStrategy())
strategy_manager.register(MeanReversionStrategy())
strategy_manager.register(ScalpingStrategy())


@router.get("")
async def list_strategies():
    return [
        {
            "name": s.name,
            "preference": s.get_market_preference(),
            "parameters": s.parameters,
        }
        for s in strategy_manager.list().values()
    ]


@router.get("/active")
async def get_active_strategy():
    return {
        "strategy": settings.strategy,
        "is_adaptive": settings.strategy == "adaptive",
        "per_symbol_strategy": settings.per_symbol_strategy,
    }


@router.post("/update")
async def update_strategy(body: StrategyUpdate, auth: str = Depends(verify_api_key)):
    if body.strategy:
        settings.strategy = body.strategy
    if body.per_symbol_strategy is not None:
        settings.per_symbol_strategy.update(body.per_symbol_strategy)
    if body.risk_per_trade is not None:
        settings.max_risk_per_trade = body.risk_per_trade
    if body.max_open_positions is not None:
        settings.max_open_positions = body.max_open_positions
    return {
        "status": "updated",
        "strategy": settings.strategy,
        "per_symbol_strategy": settings.per_symbol_strategy,
        "risk_per_trade": settings.max_risk_per_trade,
        "max_open_positions": settings.max_open_positions,
    }

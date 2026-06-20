import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.engine.market import market_data
from app.risk.manager import risk_engine
from app.worker.scheduler import scheduler

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    await init_db()
    logger.info("Database initialized")

    if settings.broker != "mt5":
        for symbol in settings.all_symbols:
            candles = await market_data.fetch_historical(symbol)
            if not candles:
                market_data.generate_synthetic(symbol, days=365)
                logger.info(f"Generated synthetic data for {symbol}")

    risk_engine.is_trading = True
    await scheduler.start()
    logger.info("Auto-trading started")

    yield
    await scheduler.stop()
    await market_data.close()
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.debug and ["*"] or ["http://localhost:3000"],
    allow_credentials=not settings.debug,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from app.routers import trading, portfolio, strategies, backtest, trades, ws, analysis

app.include_router(trading.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(ws.router, prefix="/api")
app.include_router(analysis.analysis_router, prefix="/api")
app.include_router(analysis.signal_router, prefix="/api")
app.include_router(analysis.market_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "status": "running",
        "trading": risk_engine.is_trading,
        "kill_switch": risk_engine.kill_switch,
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}

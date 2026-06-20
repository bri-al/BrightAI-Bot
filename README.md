# AI Trading Platform

A production-ready AI-powered trading system supporting Forex, Crypto, and Stocks with a full web dashboard and automated execution.

## Architecture

```
Frontend (Next.js) → FastAPI Backend → Trading Engine → Risk Manager → Execution Engine → Broker APIs
                                        ↕
                                    SQLite/PostgreSQL
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, WebSockets
- **Frontend**: Next.js 14, React 18, Tailwind CSS, Lightweight Charts
- **Trading**: numpy, pandas, custom indicator library
- **Brokers**: Binance, Alpaca, MetaTrader 5 (simulation mode by default)

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker compose up --build
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /trade/start | Start trading bot |
| POST | /trade/stop | Stop trading bot |
| POST | /trade/kill | Emergency kill switch |
| GET | /trade/status | Bot status |
| POST | /trade/execute/{symbol} | Execute single trade |
| GET | /portfolio | Portfolio overview |
| GET | /trades | Trade history |
| GET | /strategy | List strategies |
| POST | /strategy/update | Update strategy config |
| POST | /backtest | Run backtest |
| WS | /ws | Real-time updates |

## Features

- Real-time market analysis with RSI, MACD, EMA, Bollinger Bands
- Market regime detection (trend, range, volatile)
- Adaptive strategy selection based on market conditions
- Risk management with enforced limits
- Kill switch for emergency stop
- Web dashboard with candlestick charts and AI signal overlay
- Modular broker integration

## Configuration

Copy `.env.example` to `.env` and configure:
- `BROKER`: simulation, binance, alpaca, mt5
- `STRATEGY`: momentum, mean_reversion, scalping, adaptive
- Risk parameters (max drawdown, risk per trade, etc.)

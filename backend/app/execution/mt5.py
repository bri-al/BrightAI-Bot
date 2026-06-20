"""MetaTrader 5 integration - requires MT5 terminal running on the same machine."""
from typing import Optional
from app.execution.base import BaseExecutor, OrderResult
from app.config import settings

SYMBOL_MAP = {
    "EURUSD": "EURUSDm",
    "GBPUSD": "GBPUSDm",
    "USDJPY": "USDJPYm",
    "AUDUSD": "AUDUSDm",
    "USDCAD": "USDCADm",
    "USDCHF": "USDCHFm",
    "NZDUSD": "NZDUSDm",
    "XAUUSD": "XAUUSDm",
    "XAGUSD": "XAGUSDm",
    "BTCUSDT": "BTCUSDm",
    "BTCUSD": "BTCUSDm",
    "ETHUSDT": "ETHUSDm",
    "ETHUSD": "ETHUSDm",
    "SOLUSDT": "SOLUSDm",
    "SOLUSD": "SOLUSDm",
    "XRPUSDT": "XRPUSDm",
    "XRPUSD": "XRPUSDm",
    "SP500": "US500m",
    "US30": "US30m",
    "US100": "US100m",
    "UK100": "UK100m",
    "JP225": "JP225m",
    "DE30": "DE40m",
}


def _map_symbol(symbol: str) -> str:
    return SYMBOL_MAP.get(symbol, symbol)


class MT5Executor(BaseExecutor):
    def __init__(self):
        self.initialized = False
        self._mt5 = None

    @property
    def connected(self) -> bool:
        return self.initialized

    async def _ensure_init(self):
        if not self.initialized:
            try:
                import MetaTrader5 as mt5
                if not mt5.initialize(
                    path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
                    server=settings.mt5_server,
                    login=settings.mt5_login,
                    password=settings.mt5_password,
                    timeout=20000,
                ):
                    raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
                self._mt5 = mt5
                self.initialized = True
            except ImportError:
                raise RuntimeError("MetaTrader5 package not installed")

    async def _get_mt5(self):
        await self._ensure_init()
        return self._mt5

    async def _select_symbol(self, mt5, symbol: str) -> bool:
        return mt5.symbol_select(symbol, True)

    def _round_volume(self, mt5, symbol: str, size: float) -> float:
        info = mt5.symbol_info(symbol)
        if not info:
            return size
        step = info.volume_step
        if step <= 0:
            return size
        return round(size / step) * step

    async def market_order(self, symbol: str, side: str, size: float, sl: float = 0.0, tp: float = 0.0) -> OrderResult:
        try:
            mt5 = await self._get_mt5()
            mt5_symbol = _map_symbol(symbol)
            await self._select_symbol(mt5, mt5_symbol)
            size = self._round_volume(mt5, mt5_symbol, size)

            tick = mt5.symbol_info_tick(mt5_symbol)
            if not tick or (tick.ask == 0.0 and tick.bid == 0.0):
                return OrderResult(success=False, message=f"Market closed or no price for {symbol}")

            price = tick.ask if side == "buy" else tick.bid
            order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": mt5_symbol,
                "volume": size,
                "type": order_type,
                "price": price,
                "deviation": 10,
                "magic": 123456,
                "comment": "AI Trade",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            if sl > 0:
                request["sl"] = round(sl, int(mt5.symbol_info(mt5_symbol).digits))
            if tp > 0:
                request["tp"] = round(tp, int(mt5.symbol_info(mt5_symbol).digits))
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(success=False, message=f"MT5 error ({result.retcode}): {result.comment}")
            return OrderResult(
                success=True,
                order_id=str(result.order),
                filled_price=result.price,
                filled_size=result.volume,
                message=f"MT5 {side} {symbol} @ {result.price}",
            )
        except Exception as e:
            return OrderResult(success=False, message=str(e))

    async def limit_order(self, symbol: str, side: str, size: float, price: float) -> OrderResult:
        try:
            mt5 = await self._get_mt5()
            mt5_symbol = _map_symbol(symbol)
            await self._select_symbol(mt5, mt5_symbol)
            size = self._round_volume(mt5, mt5_symbol, size)

            order_type = mt5.ORDER_TYPE_BUY_LIMIT if side == "buy" else mt5.ORDER_TYPE_SELL_LIMIT
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": mt5_symbol,
                "volume": size,
                "type": order_type,
                "price": price,
                "magic": 123456,
                "comment": "AI Limit Order",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(success=False, message=f"MT5 error ({result.retcode}): {result.comment}")
            return OrderResult(success=True, order_id=str(result.order))
        except Exception as e:
            return OrderResult(success=False, message=str(e))

    async def stop_loss_order(self, symbol: str, side: str, size: float, stop_price: float) -> OrderResult:
        try:
            mt5 = await self._get_mt5()
            mt5_symbol = _map_symbol(symbol)
            await self._select_symbol(mt5, mt5_symbol)
            size = self._round_volume(mt5, mt5_symbol, size)

            tick = mt5.symbol_info_tick(mt5_symbol)
            if not tick or (tick.ask == 0.0 and tick.bid == 0.0):
                return OrderResult(success=False, message=f"Market closed or no price for {symbol}")

            order_type = mt5.ORDER_TYPE_SELL if side == "buy" else mt5.ORDER_TYPE_BUY
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": mt5_symbol,
                "volume": size,
                "type": order_type,
                "price": stop_price,
                "sl": 0.0,
                "tp": 0.0,
                "deviation": 10,
                "magic": 123456,
                "comment": "AI Stop Loss",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(success=False, message=f"MT5 error ({result.retcode}): {result.comment}")
            return OrderResult(success=True, order_id=str(result.order))
        except Exception as e:
            return OrderResult(success=False, message=str(e))

    async def cancel_order(self, order_id: str) -> bool:
        try:
            mt5 = await self._get_mt5()
            return mt5.order_delete(int(order_id))
        except Exception:
            return False

    async def get_position(self, symbol: str) -> Optional[dict]:
        try:
            mt5 = await self._get_mt5()
            mt5_symbol = _map_symbol(symbol)
            positions = mt5.positions_get(symbol=mt5_symbol)
            if positions and len(positions) > 0:
                pos = positions[0]
                return {
                    "symbol": symbol,
                    "size": pos.volume,
                    "entry": pos.price_open,
                    "profit": pos.profit,
                }
            return None
        except Exception:
            return None

    async def get_all_positions(self) -> list[dict]:
        try:
            mt5 = await self._get_mt5()
            positions = mt5.positions_get()
            if not positions:
                return []
            result = []
            for pos in positions:
                sym = pos.symbol
                for our_sym, mt5_sym in SYMBOL_MAP.items():
                    if mt5_sym == sym:
                        sym = our_sym
                        break
                result.append({
                    "symbol": sym,
                    "direction": "long" if pos.type == 0 else "short",
                    "size": pos.volume,
                    "entry": pos.price_open,
                    "current": pos.price_current,
                    "profit": pos.profit,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "ticket": pos.ticket,
                    "magic": pos.magic,
                })
            return result
        except Exception:
            return []

    async def get_account(self) -> dict:
        try:
            mt5 = await self._get_mt5()
            info = self._mt5.account_info()
            if info:
                return {
                    "balance": info.balance,
                    "equity": info.equity,
                    "margin": info.margin,
                    "profit": info.profit,
                }
            return {"balance": 0, "equity": 0}
        except Exception:
            return {"balance": 0, "equity": 0}

    async def get_price(self, symbol: str) -> float:
        try:
            mt5 = await self._get_mt5()
            mt5_symbol = _map_symbol(symbol)
            await self._select_symbol(mt5, mt5_symbol)
            tick = mt5.symbol_info_tick(mt5_symbol)
            return (tick.ask + tick.bid) / 2 if tick else 0.0
        except Exception:
            return 0.0

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

ws_clients: set[WebSocket] = set()


async def broadcast(message: dict):
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        ws_clients.discard(ws)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
            elif msg.get("type") == "subscribe":
                symbol = msg.get("symbol", "BTCUSDT")
                await ws.send_json({"type": "subscribed", "symbol": symbol})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_clients.discard(ws)

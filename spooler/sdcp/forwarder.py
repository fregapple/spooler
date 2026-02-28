import asyncio
import json

import websockets

# Track all connected GUI clients
clients = set()


async def ws_handler(websocket):
    """Handle a new GUI connection."""
    clients.add(websocket)
    try:
        # Keep the connection open until the client disconnects
        async for _ in websocket:
            pass
    finally:
        clients.remove(websocket)


async def start_forwarder():
    """
    Start the local WebSocket server that the GUI connects to.
    Call this once during daemon startup.
    """
    return await websockets.serve(ws_handler, "localhost", 8765)


async def forward(message_type: str, payload: dict):
    """
    Send a typed message to all connected GUI clients.
    Example:
        await forward("sdcp", parsed_packet)
        await forward("log", {...})
        await forward("config", {...})
    """
    if not clients:
        return  # No GUI connected — silently ignore

    packet = {"type": message_type, "data": payload}

    data = json.dumps(packet)

    # Send to all clients, ignore failures
    await asyncio.gather(*(ws.send(data) for ws in clients), return_exceptions=True)


async def broadcast(payload: dict):
    """
    Legacy helper: broadcast raw payload without a type.
    You can still use this if needed, but forward() is preferred.
    """
    if not clients:
        return

    data = json.dumps(payload)

    await asyncio.gather(*(ws.send(data) for ws in clients), return_exceptions=True)

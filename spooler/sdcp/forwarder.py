import asyncio
import json
import os

import websockets

# Track all connected GUI clients
clients = set()
control_queue = asyncio.Queue()


def _json_default(value):
    """Convert non-JSON-native values to safe wire representations."""
    if isinstance(value, (bytes, bytearray)):
        try:
            return bytes(value).decode("utf-8")
        except Exception:
            return bytes(value).hex()

    # Last-resort fallback keeps forwarding alive instead of dropping updates.
    return str(value)


async def ws_handler(websocket):
    """Handle a new GUI connection."""
    clients.add(websocket)
    try:
        async for raw in websocket:
            try:
                message = json.loads(raw)
            except Exception:
                continue

            if isinstance(message, dict):
                await control_queue.put(message)
    finally:
        clients.remove(websocket)


async def start_forwarder():
    """
    Start the local WebSocket server that the GUI connects to.
    Call this once during daemon startup.
    """
    host = os.getenv("SPOOLER_FORWARDER_HOST", "127.0.0.1")
    port = int(os.getenv("SPOOLER_FORWARDER_PORT", "8765"))
    return await websockets.serve(ws_handler, host, port)


def get_control_queue():
    """Return the queue of control messages received from GUI clients."""
    return control_queue


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

    data = json.dumps(packet, default=_json_default)

    # Send to all clients, ignore failures
    await asyncio.gather(*(ws.send(data) for ws in clients), return_exceptions=True)


async def broadcast(payload: dict):
    """
    Legacy helper: broadcast raw payload without a type.
    You can still use this if needed, but forward() is preferred.
    """
    if not clients:
        return

    data = json.dumps(payload, default=_json_default)

    await asyncio.gather(*(ws.send(data) for ws in clients), return_exceptions=True)

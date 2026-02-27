import asyncio
import json

async def keepalive(ws):
    while True:
        try:
            await ws.send(json.dumps({"Cmd": "ping"}))
        except:
            return
        await asyncio.sleep(10)
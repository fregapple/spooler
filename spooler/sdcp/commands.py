import json

async def list_printer_files(machine_id, ws):
    await ws.send(json.dumps({
        "Cmd": 258,
        "MainboardID": machine_id
    }))
import json


async def send_cmd(ws, payload):
    """Send raw SDCP JSON payload."""
    await ws.send(json.dumps(payload))


async def list_printer_files(ws, machine_id):
    payload = {
        "Id": "uuid-string",
        "Data": {
            "Cmd": 258,
            "Data": {"Url": "/local"},
            "RequestID": "uuid-string",
            "MainboardID": "string",
            "TimeStamp": 1687069655,
            "From": 0,
        },
        "Topic": f"sdcp/request/{machine_id}",
    }

    await send_cmd(ws, payload)


async def delete_printer_files(ws, file_list, machine_id):
    payload = {
        "Id": "uuid-string",
        "Data": {
            "Cmd": 259,
            "Data": {"FileList": file_list},
            "RequestID": "uuid-string",
            "MainboardID": "string",
            "TimeStamp": 1687069655,
            "From": 0,
        },
        "Topic": f"sdcp/request/{machine_id}",
    }

    await send_cmd(ws, payload)

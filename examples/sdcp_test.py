import asyncio
import json

import websockets
from sdcp.commands import delete_printer_files, list_printer_files

SDCP_URL = "ws://192.168.1.127:3030/websocket?'command'='subscribe'"  # replace with your printer's IP
MACHINE_ID = "047012980103147000001c0000000000"  # paste manually for now
FILE_LIST = []


async def listener(ws):
    """Print every incoming SDCP message."""
    async for msg in ws:
        try:
            data = json.loads(msg)
        except Exception:
            print("Non‑JSON:", msg)
            continue

        try:
            if data["Data"]["Cmd"] == 258:
                FILE_DICT = data["Data"]["Data"]["FileList"]
                for file in FILE_DICT:
                    FILE_LIST.append(file["name"])
                    print(file)
        except Exception as e:
            print(f"Format error: {e}")
            pass

        # print("\n--- Incoming SDCP Message ---")
        # print(json.dumps(data, indent=2))


async def main():
    async with websockets.connect(SDCP_URL) as ws:
        print("Connected to SDCP WebSocket")

        # Start listener in background
        asyncio.create_task(listener(ws))

        # Give the connection a moment to settle
        await asyncio.sleep(1)

        # Test: list files
        print("Sending list_printer_files()…")
        await list_printer_files(ws, MACHINE_ID)

        # Test: Delete files
        print("Sending delete_printer_files()...")
        await delete_printer_files(
            ws,
            ["/local/ECC_0.4_House Box Units (Targaryen)]_0.2_2h14m.gcode"],
            MACHINE_ID,
        )

        # Keep alive so listener runs
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())

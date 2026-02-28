import asyncio
import json

import websockets
from ui.progress import render_progress
from utils.colors import SDCP

from sdcp import events
from sdcp.forwarder import forward
from sdcp.keepalive import keepalive
from sdcp.parser import parse_message
from sdcp.state import PrintState


async def sdcp_listener(config, log, devices=None):
    state = PrintState()
    spin_index = 0

    while True:
        try:
            log.info(SDCP, f"Connecting to {config.sdcp_ws_url}...")
            async with websockets.connect(config.sdcp_ws_url) as ws:
                log.info(SDCP, "Connected to SDCP WebSocket")

                # Start keepalive
                asyncio.create_task(keepalive(ws))

                async for raw in ws:
                    msg = json.loads(raw)
                    parsed = parse_message(msg)
                    if not parsed:
                        continue

                    # Attempt to forward to GUI

                    try:
                        await forward("sdcp", parsed)
                    except Exception:
                        pass

                    machine_status = parsed["machine_status"]
                    print_status = parsed["print_status"]
                    progress = parsed["progress"]
                    filename = parsed["filename"]
                    total_extrusions = parsed["printinfo"].get("54 6F 74 61 6C 45 78 74 72 75 73 69 6F 6E 00")

                    # Update state
                    if filename and filename.strip():
                        state.filename = filename
                        state.shortname = filename.split(".gcode")[0]
                    state.total_extrusions = total_extrusions

                    # -----------------------------
                    # PRINT START + PREHEAT
                    # -----------------------------
                    if machine_status == [1] and (print_status == 16 or print_status == 13) and not state.active:
                        await events.handle_print_start(state, devices, config, log)

                    # -----------------------------
                    # PRINT PAUSE
                    # -----------------------------
                    if print_status == 6 and not state.paused:
                        await events.handle_print_pause(state, devices, config, log)

                    # -----------------------------
                    # PRINT RESUME
                    # -----------------------------
                    if print_status == 13 and (state.paused or state.stopped):
                        await events.handle_print_resume(state, devices, config, log)

                    # -----------------------------
                    # PRINT STOP
                    # -----------------------------
                    if print_status == 8 and state.active:
                        await events.handle_print_stop(state, devices, config, log)

                    # -----------------------------
                    # PRINT COMPLETE
                    # -----------------------------
                    if machine_status == [0] and state.active:
                        await events.handle_print_complete(state, devices, config, log)

                    # -----------------------------
                    # IDLE
                    # -----------------------------
                    if state.waiting_for_idle and print_status in (0, 9):
                        await events.handle_idle(state, devices, config, log)

                    # -----------------------------
                    # PROGRESS BAR
                    # -----------------------------
                    if state.active:
                        spin_index += 1
                        print(render_progress(progress, spin_index), end="", flush=True)

        except Exception as e:
            log.error(SDCP, f"Connection error: {e}")
            log.info(SDCP, "Reconnecting in 3 seconds...")
            await asyncio.sleep(3)

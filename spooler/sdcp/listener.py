import asyncio
import json
import time
import uuid

import websockets
from utils.colors import SDCP

from sdcp.commands import send_cmd
from sdcp import events
from sdcp.forwarder import forward
from sdcp.keepalive import keepalive
from sdcp.parser import parse_message
from sdcp.state import PrintState


def _resolve_printer_id(config):
    printers = getattr(config, "printers", None)
    if isinstance(printers, list):
        for printer in printers:
            if isinstance(printer, dict) and printer.get("enabled", True):
                return printer.get("id", "printer-01")
        for printer in printers:
            if isinstance(printer, dict):
                return printer.get("id", "printer-01")
    return "printer-01"


def _extract_mainboard_id(msg):
    """Best-effort extraction of SDCP mainboard ID from topic or payload."""
    if not isinstance(msg, dict):
        return None

    topic = msg.get("Topic")
    if isinstance(topic, str) and topic:
        parts = topic.split("/")
        if parts:
            candidate = parts[-1].strip()
            if candidate:
                return candidate

    data = msg.get("Data")
    if isinstance(data, dict):
        candidate = data.get("MainboardID")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    return None


async def _handle_sdcp_command(ws, command, log, default_machine_id):
    if not isinstance(command, dict):
        return

    purpose = command.get("purpose")
    payload = command.get("payload")
    if isinstance(payload, dict):
        await send_cmd(ws, payload)
        request_id = None
        if isinstance(payload.get("Data"), dict):
            request_id = payload["Data"].get("RequestID")
        return {
            "request_id": request_id,
            "purpose": purpose,
        }

    cmd = command.get("cmd")
    if cmd is None:
        return

    try:
        cmd = int(cmd)
    except Exception:
        log.warn(SDCP, f"Ignoring SDCP command with invalid cmd value: {cmd!r}")
        return

    data = command.get("data", {})
    topic = command.get("topic")
    machine_id = command.get("machine_id") or default_machine_id

    if not topic:
        topic = f"sdcp/request/{machine_id}"

    request_id = str(command.get("request_id_hint") or uuid.uuid4())

    payload = {
        "Id": request_id,
        "Data": {
            "Cmd": cmd,
            "Data": data if isinstance(data, dict) else {},
            "RequestID": request_id,
            "MainboardID": str(machine_id),
            "TimeStamp": int(time.time()),
            "From": 1,
        },
        "Topic": topic,
    }

    await send_cmd(ws, payload)
    return {
        "request_id": request_id,
        "cmd": cmd,
        "topic": topic,
        "machine_id": str(machine_id),
        "purpose": purpose,
    }


async def sdcp_listener(config, log, devices=None, command_queue=None):
    state = PrintState()
    printer_id = _resolve_printer_id(config)
    command_machine_id = printer_id

    while True:
        try:
            log.info(SDCP, f"Connecting to {config.sdcp_ws_url}...")
            async with websockets.connect(config.sdcp_ws_url) as ws:
                log.info(SDCP, "Connected to SDCP WebSocket")

                # Start keepalive
                asyncio.create_task(keepalive(ws))

                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        msg = json.loads(raw)

                        observed_machine_id = _extract_mainboard_id(msg)
                        if observed_machine_id:
                            command_machine_id = observed_machine_id

                        # Forward full SDCP payloads so GUI can inspect command responses.
                        try:
                            await forward("sdcp_raw", {"printer_id": printer_id, "packet": msg})
                        except Exception:
                            pass

                        parsed = parse_message(msg)
                        if parsed:
                            parsed["printer_id"] = printer_id

                            # Attempt to forward to GUI
                            try:
                                await forward("sdcp", parsed)
                            except Exception:
                                pass

                            machine_status = parsed["machine_status"]
                            print_status = parsed["print_status"]
                            filename = parsed["filename"]
                            total_extrusions = parsed["printinfo"].get(
                                "54 6F 74 61 6C 45 78 74 72 75 73 69 6F 6E 00"
                            )

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

                    except asyncio.TimeoutError:
                        pass

                    # Handle queued SDCP commands from WebGUI
                    if command_queue is not None:
                        while True:
                            try:
                                queued_command = command_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break

                            try:
                                result = await _handle_sdcp_command(
                                    ws,
                                    queued_command,
                                    log,
                                    command_machine_id,
                                )

                                await forward(
                                    "control_result",
                                    {
                                        "type": "sdcp_command",
                                        "ok": True,
                                        "message": "SDCP command sent",
                                        **(result or {}),
                                    },
                                )
                            except Exception as exc:
                                log.error(SDCP, f"Failed to send SDCP command: {exc}")
                                await forward(
                                    "control_result",
                                    {
                                        "type": "sdcp_command",
                                        "ok": False,
                                        "error": str(exc),
                                    },
                                )

        except Exception as e:
            log.error(SDCP, f"Connection error: {e}")
            log.info(SDCP, "Reconnecting in 3 seconds...")
            await asyncio.sleep(3)

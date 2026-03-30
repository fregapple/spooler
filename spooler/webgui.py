import asyncio
import json
import os
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path

import websockets
import yaml
from nicegui import ui

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "config.yaml"
FORWARDER_URL = os.getenv("SPOOLER_FORWARDER_URL", "ws://127.0.0.1:8765")


def default_config():
    return {
        "schema_version": 2,
        "setup": {"completed": False},
        "global": {
            "log_level": "INFO",
            "log_timestamps": True,
            "always_running": False,
            "delete_after_print": True,
            "hide_one_time_mode_terminal": False,
        },
        "spoolman": {
            "enabled": True,
            "url": "http://localhost:7912",
            "fallback_url": "http://localhost:7912",
        },
        "notifications": {
            "enabled": True,
            "apprise_url": "",
            "apprise_config": "apprise",
            "tags": {"custom": "spooler", "spoolman": "spoolman"},
        },
        "printers": [
            {
                "id": "printer-01",
                "name": "Primary Printer",
                "enabled": True,
                "sdcp_ws_url": "",
                "watch_folder": str(ROOT_DIR / "watch"),
                "delete_after_print": True,
            }
        ],
        "devices": [],
        "assignments": [],
    }


def ensure_mapping(parent, key, fallback):
    value = parent.get(key)
    if not isinstance(value, dict):
        parent[key] = dict(fallback)
    return parent[key]


def normalize_config(config):
    if not isinstance(config, dict):
        config = default_config()

    defaults = default_config()

    config.setdefault("schema_version", defaults["schema_version"])
    setup = ensure_mapping(config, "setup", defaults["setup"])
    setup.setdefault("completed", False)

    global_cfg = ensure_mapping(config, "global", defaults["global"])
    for key, value in defaults["global"].items():
        global_cfg.setdefault(key, value)

    spoolman_cfg = ensure_mapping(config, "spoolman", defaults["spoolman"])
    for key, value in defaults["spoolman"].items():
        spoolman_cfg.setdefault(key, value)

    notifications_cfg = ensure_mapping(config, "notifications", defaults["notifications"])
    for key, value in defaults["notifications"].items():
        notifications_cfg.setdefault(key, value)

    tags_cfg = ensure_mapping(notifications_cfg, "tags", defaults["notifications"]["tags"])
    for key, value in defaults["notifications"]["tags"].items():
        tags_cfg.setdefault(key, value)

    if not isinstance(config.get("printers"), list):
        config["printers"] = []
    if not config["printers"]:
        config["printers"].append(defaults["printers"][0].copy())

    for printer in config["printers"]:
        if not isinstance(printer, dict):
            continue
        for key, value in defaults["printers"][0].items():
            printer.setdefault(key, value)

    if not isinstance(config.get("devices"), list):
        config["devices"] = []

    for device in config["devices"]:
        if not isinstance(device, dict):
            continue
        device.setdefault("id", "")
        device.setdefault("device_type", "airpurifier")
        device.setdefault("model", "")
        device.setdefault("always_on", False)
        connection = ensure_mapping(device, "connection", {"device_id": "", "local_key": "", "ip": "Auto"})
        connection.setdefault("device_id", "")
        connection.setdefault("local_key", "")
        connection.setdefault("ip", "Auto")

    if not isinstance(config.get("assignments"), list):
        config["assignments"] = []

    for assignment in config["assignments"]:
        if not isinstance(assignment, dict):
            continue
        assignment.setdefault("device_id", "")
        if not isinstance(assignment.get("printer_ids"), list):
            assignment["printer_ids"] = []
        policy = ensure_mapping(
            assignment,
            "policy",
            {
                "turn_on_when_any_printing": True,
                "turn_off_when_all_idle": True,
                "idle_grace_seconds": 180,
            },
        )
        policy.setdefault("turn_on_when_any_printing", True)
        policy.setdefault("turn_off_when_all_idle", True)
        policy.setdefault("idle_grace_seconds", 180)

    return config


def load_config_from_disk():
    if not CONFIG_PATH.exists():
        return default_config()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return normalize_config(data)


def save_config_to_disk(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False)


def set_key(target, key, value):
    target[key] = value


def set_int_key(target, key, value):
    try:
        target[key] = int(value)
    except (TypeError, ValueError):
        target[key] = 0


def parse_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def add_runtime_log(level, tag, message):
    ts = datetime.now().strftime("%H:%M:%S")
    state["runtime"]["logs"].append(f"{ts} [{level}] {tag} {message}")


def safe_notify(message, notify_type="info"):
    """Guard notifications for async tasks where the originating UI slot may be gone."""
    try:
        ui.notify(message, type=notify_type)
    except RuntimeError:
        # Client/page may have been closed or re-rendered while async task was running.
        pass


state = {
    "config": normalize_config(load_config_from_disk()),
    "runtime": {
        "connected": False,
        "last_error": "",
        "printer_stats": {},
        "device_states": [],
        "devices_meta": [],
        "control_feedback": deque(maxlen=20),
        "logs": deque(maxlen=400),
        "forwarder_ws": None,
        "webcam": {
            "stream_url": "",
            "last_error": "",
            "pending_request_ids": set(),
            "last_mainboard_id": "",
        },
    },
    "sdcp_form": {
        "cmd": "258",
        "machine_id": "",
        "topic": "",
        "data_json": '{"Url": "/local"}',
        "raw_payload": "",
    },
}
raw_yaml_editor = None
_forwarder_task = None


def get_printer_ids():
    ids = []
    for printer in state["config"].get("printers", []):
        if isinstance(printer, dict):
            printer_id = str(printer.get("id", "")).strip()
            if printer_id and printer_id not in ids:
                ids.append(printer_id)

    for printer_id in state["runtime"]["printer_stats"].keys():
        if printer_id not in ids:
            ids.append(printer_id)

    return ids or ["printer-01"]


def get_printer_name(printer_id):
    for printer in state["config"].get("printers", []):
        if isinstance(printer, dict) and printer.get("id") == printer_id:
            return printer.get("name") or printer_id
    return printer_id


def refresh_all_views():
    render_overview.refresh()
    render_wizard.refresh()
    render_controls.refresh()
    render_logs.refresh()
    sync_editor_from_state()


def save_clicked():
    save_config_to_disk(state["config"])
    ui.notify(f"Saved YAML config to {CONFIG_PATH}", type="positive")


def reload_clicked():
    try:
        state["config"] = normalize_config(load_config_from_disk())
        refresh_all_views()
        ui.notify("Reloaded YAML config from disk", type="positive")
    except Exception as exc:
        ui.notify(f"Failed to reload config: {exc}", type="negative")


def sync_editor_from_state():
    if raw_yaml_editor is not None:
        raw_yaml_editor.value = yaml.safe_dump(state["config"], sort_keys=False)


def apply_editor_yaml():
    if raw_yaml_editor is None:
        return

    try:
        parsed = yaml.safe_load(raw_yaml_editor.value) or {}
        state["config"] = normalize_config(parsed)
        render_overview.refresh()
        render_wizard.refresh()
        render_controls.refresh()
        ui.notify("Applied YAML from editor", type="positive")
    except Exception as exc:
        ui.notify(f"Invalid YAML: {exc}", type="negative")


async def send_control_message(message):
    ws = state["runtime"].get("forwarder_ws")
    if ws is None:
        safe_notify("Not connected to daemon forwarder", notify_type="warning")
        return

    try:
        await ws.send(json.dumps(message))
    except Exception as exc:
        safe_notify(f"Failed to send command: {exc}", notify_type="negative")


def send_device_command(action, value=None):
    payload = {
        "type": "device_command",
        "data": {
            "device_type": "airpurifier",
            "action": action,
            "value": value,
        },
    }
    asyncio.create_task(send_control_message(payload))

def _extract_request_id_from_sdcp(packet):
    if not isinstance(packet, dict):
        return None
    if isinstance(packet.get("Data"), dict):
        data = packet["Data"]
        return data.get("RequestID") or data.get("request_id")
    return packet.get("RequestID") or packet.get("request_id") or packet.get("Id")


def _extract_cmd_from_sdcp(packet):
    if not isinstance(packet, dict):
        return None
    if isinstance(packet.get("Data"), dict):
        return packet["Data"].get("Cmd")
    return packet.get("Cmd")


def _extract_mainboard_id_from_sdcp(packet):
    if not isinstance(packet, dict):
        return None

    topic = packet.get("Topic")
    if isinstance(topic, str) and topic:
        parts = topic.split("/")
        if parts and parts[-1].strip():
            return parts[-1].strip()

    data = packet.get("Data")
    if isinstance(data, dict):
        candidate = data.get("MainboardID")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    return None


def _extract_webcam_url_from_sdcp(packet):
    """Find likely webcam stream URL fields in SDCP payloads."""

    def _normalize_candidate_url(text):
        if not isinstance(text, str):
            return None

        candidate = text.strip()
        if not candidate:
            return None

        # Already absolute.
        if candidate.startswith(("http://", "https://", "rtsp://", "ws://", "wss://", "rtmp://")):
            return candidate

        # Some SDCP replies return VideoUrl like "192.168.1.127:3031/video".
        if "/" in candidate and ":" in candidate and " " not in candidate:
            return f"http://{candidate}"

        return None

    def _walk(value):
        if isinstance(value, dict):
            for key, val in value.items():
                key_lower = str(key).lower()
                if isinstance(val, str):
                    val_lower = val.lower()
                    if "url" in key_lower or "stream" in key_lower or "webcam" in key_lower:
                        normalized = _normalize_candidate_url(val)
                        if normalized:
                            return normalized

                    if (
                        val_lower.startswith(("http://", "https://", "rtsp://", "ws://", "wss://", "rtmp://"))
                        and ("stream" in val_lower or "webcam" in val_lower or "mjpg" in val_lower)
                    ):
                        return val

                found = _walk(val)
                if found:
                    return found

        elif isinstance(value, list):
            for item in value:
                found = _walk(item)
                if found:
                    return found

        return None

    return _walk(packet)


async def get_stream_url():
    request_id = str(uuid.uuid4())
    machine_id = str(state["sdcp_form"].get("machine_id", "")).strip()

    message = {
        "type": "sdcp_command",
        "data": {
            "cmd": 386,
            "data": {"Enable": 1},
            "purpose": "webcam_url",
            "request_id_hint": request_id,
        },
    }

    if machine_id:
        message["data"]["machine_id"] = machine_id

    state["runtime"]["webcam"]["last_error"] = ""
    await send_control_message(message)
    return request_id

def send_sdcp_form_command():
    form = state["sdcp_form"]
    try:
        cmd = int(str(form.get("cmd", "")).strip())
    except Exception:
        safe_notify("SDCP cmd must be an integer", notify_type="negative")
        return

    data_json = str(form.get("data_json", "")).strip()
    if data_json:
        try:
            data = json.loads(data_json)
            if not isinstance(data, dict):
                raise ValueError("data_json must decode to an object")
        except Exception as exc:
            safe_notify(f"Invalid SDCP data JSON: {exc}", notify_type="negative")
            return
    else:
        data = {}

    message = {
        "type": "sdcp_command",
        "data": {
            "cmd": cmd,
            "data": data,
        },
    }

    machine_id = str(form.get("machine_id", "")).strip()
    topic = str(form.get("topic", "")).strip()
    if machine_id:
        message["data"]["machine_id"] = machine_id
    if topic:
        message["data"]["topic"] = topic

    asyncio.create_task(send_control_message(message))


def send_sdcp_raw_payload():
    raw = str(state["sdcp_form"].get("raw_payload", "")).strip()
    if not raw:
        safe_notify("Raw payload is empty", notify_type="warning")
        return

    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
    except Exception as exc:
        safe_notify(f"Invalid raw payload JSON: {exc}", notify_type="negative")
        return

    message = {
        "type": "sdcp_command",
        "data": {
            "payload": payload,
        },
    }

    asyncio.create_task(send_control_message(message))


def add_printer():
    state["config"]["printers"].append(
        {
            "id": f"printer-{len(state['config']['printers']) + 1:02d}",
            "name": "New Printer",
            "enabled": True,
            "sdcp_ws_url": "",
            "watch_folder": str(ROOT_DIR / "watch"),
            "delete_after_print": True,
        }
    )
    render_wizard.refresh()
    render_overview.refresh()


def remove_printer(index):
    if len(state["config"]["printers"]) <= 1:
        ui.notify("At least one printer is required", type="warning")
        return
    state["config"]["printers"].pop(index)
    render_wizard.refresh()
    render_overview.refresh()


def add_device():
    state["config"]["devices"].append(
        {
            "id": f"device-{len(state['config']['devices']) + 1:02d}",
            "device_type": "airpurifier",
            "model": "",
            "always_on": False,
            "connection": {"device_id": "", "local_key": "", "ip": "Auto"},
        }
    )
    render_wizard.refresh()
    render_overview.refresh()


def remove_device(index):
    state["config"]["devices"].pop(index)
    render_wizard.refresh()
    render_overview.refresh()


def add_assignment():
    state["config"]["assignments"].append(
        {
            "device_id": "",
            "printer_ids": [],
            "policy": {
                "turn_on_when_any_printing": True,
                "turn_off_when_all_idle": True,
                "idle_grace_seconds": 180,
            },
        }
    )
    render_wizard.refresh()


def remove_assignment(index):
    state["config"]["assignments"].pop(index)
    render_wizard.refresh()


def handle_forward_packet(packet):
    if not isinstance(packet, dict):
        return

    message_type = packet.get("type")
    data = packet.get("data")

    if message_type == "sdcp" and isinstance(data, dict):
        printer_id = str(data.get("printer_id") or "printer-01")
        state["runtime"]["printer_stats"][printer_id] = data

    elif message_type == "sdcp_raw" and isinstance(data, dict):
        raw_packet = data.get("packet") if isinstance(data.get("packet"), dict) else {}
        mainboard_id = _extract_mainboard_id_from_sdcp(raw_packet)
        if mainboard_id:
            state["runtime"]["webcam"]["last_mainboard_id"] = mainboard_id

        response_request_id = _extract_request_id_from_sdcp(raw_packet)
        response_cmd = _extract_cmd_from_sdcp(raw_packet)

        pending_ids = state["runtime"]["webcam"]["pending_request_ids"]
        is_webcam_response = (response_request_id in pending_ids) or (response_cmd == 386)

        if is_webcam_response:
            stream_url = _extract_webcam_url_from_sdcp(raw_packet)
            if stream_url:
                state["runtime"]["webcam"]["stream_url"] = stream_url
                state["runtime"]["webcam"]["last_error"] = ""
                if response_request_id in pending_ids:
                    pending_ids.discard(response_request_id)
                add_runtime_log("INFO", "[WEBCAM]", f"Stream URL received: {stream_url}")
            elif response_request_id in pending_ids:
                add_runtime_log(
                    "WARN",
                    "[WEBCAM]",
                    (
                        "Webcam response received without URL "
                        f"(cmd={response_cmd}, request_id={response_request_id})"
                    ),
                )

    elif message_type == "device_state" and isinstance(data, dict):
        devices = data.get("devices")
        if isinstance(devices, list):
            state["runtime"]["device_states"] = devices

    elif message_type == "devices" and isinstance(data, list):
        state["runtime"]["devices_meta"] = data

    elif message_type == "log" and isinstance(data, dict):
        add_runtime_log(data.get("level", "INFO"), data.get("tag", ""), data.get("message", ""))

    elif message_type == "control_result" and isinstance(data, dict):
        state["runtime"]["control_feedback"].appendleft(data)

        if data.get("type") == "sdcp_command" and data.get("purpose") == "webcam_url" and data.get("ok"):
            request_id = data.get("request_id")
            if request_id:
                state["runtime"]["webcam"]["pending_request_ids"].add(request_id)
                add_runtime_log("INFO", "[WEBCAM]", f"Webcam URL request queued ({request_id})")

        if data.get("ok"):
            add_runtime_log("INFO", "[CONTROL]", data.get("message", "Command completed"))
        else:
            add_runtime_log("ERROR", "[CONTROL]", data.get("error", "Command failed"))


def format_forwarder_error(exc):
    text = str(exc)
    if isinstance(exc, ConnectionRefusedError):
        return f"Waiting for daemon at {FORWARDER_URL}"
    if "Connect call failed" in text or "Errno 111" in text:
        return f"Waiting for daemon at {FORWARDER_URL}"
    return text


async def forwarder_loop():
    while True:
        try:
            async with websockets.connect(FORWARDER_URL) as ws:
                state["runtime"]["connected"] = True
                state["runtime"]["last_error"] = ""
                state["runtime"]["forwarder_ws"] = ws
                add_runtime_log("INFO", "[FORWARDER]", "Connected to daemon stream")

                while True:
                    raw = await ws.recv()
                    try:
                        packet = json.loads(raw)
                    except Exception:
                        continue
                    handle_forward_packet(packet)

        except Exception as exc:
            was_connected = state["runtime"]["connected"]
            previous_error = state["runtime"]["last_error"]
            error_text = format_forwarder_error(exc)

            state["runtime"]["connected"] = False
            state["runtime"]["forwarder_ws"] = None
            state["runtime"]["last_error"] = error_text

            # Keep reconnects quiet unless status changed, to avoid log spam while daemon is down.
            if was_connected or previous_error != error_text:
                add_runtime_log("WARN", "[FORWARDER]", f"Disconnected: {error_text}")

            await asyncio.sleep(2)


def ensure_background_tasks():
    global _forwarder_task
    if _forwarder_task is None or _forwarder_task.done():
        _forwarder_task = asyncio.create_task(forwarder_loop())

def normalise_printer_status(status):
    if status == 0:
        return "Idle"
    elif status == 1:
        return "Homing"
    elif status == 2:
        return "Dropping Filament"
    elif status == 3:
        return "Exposuring?"
    elif status == 4:
        return "Lifting Hotend?"
    elif status == 5:
        return "Pausing"
    elif status == 6:
        return "Paused"
    elif status == 7:
        return "Stopping"
    elif status == 8:
        return "Stopped"
    elif status == 9:
        return "Print Complete"
    elif status == 10:
        return "File Checking"
    elif status == 13:
        return "Printing"
    else:
        return f"Status {status}"

def normalise_machine_status(status):
    if status == [0]:
        return "Idle"
    elif status == [1]:
        return "Active"
    elif status == [2]:
        return "File Transferring"
    elif status == [3]:
        return "Calibrating"
    elif status == [4]:
        return "Device Testing"
    elif status == [5]:
        return "Auto Leveling"
    else:
        return f"Status {status}"

async def show_stream():
    state["runtime"]["webcam"]["stream_url"] = ""
    state["runtime"]["webcam"]["last_error"] = ""
    render_webcam_panel.refresh()
    await get_stream_url()

    timeout_seconds = 10
    poll_interval = 0.2
    loops = int(timeout_seconds / poll_interval)

    for _ in range(loops):
        if state["runtime"]["webcam"].get("stream_url"):
            safe_notify("Webcam stream URL received", notify_type="positive")
            render_webcam_panel.refresh()
            return
        await asyncio.sleep(poll_interval)

    state["runtime"]["webcam"]["last_error"] = "Timed out waiting for webcam URL response"
    safe_notify("Timed out waiting for webcam URL", notify_type="warning")
    render_webcam_panel.refresh()

def hide_stream():
    state["runtime"]["webcam"]["stream_url"] = ""
    state["runtime"]["webcam"]["last_error"] = ""
    state["runtime"]["webcam"]["pending_request_ids"].clear()
    render_webcam_panel.refresh()

@ui.refreshable
def render_overview_status():
    cfg = state["config"]

    printer_ids = get_printer_ids()

    with ui.card().classes("w-full max-w-[1600px] mx-auto"):

        with ui.column().classes("w-full items-center"):
            ui.label("Live Printer Status").classes("text-h6")

        # --- Tabs ---
        with ui.tabs().classes("w-full") as tabs:
            tab_refs = []
            for printer_id in printer_ids:
                tab_refs.append(ui.tab(get_printer_name(printer_id), icon="print"))

        # --- Tab Panels ---
        with ui.tab_panels(tabs, value=tab_refs[0]).classes("w-full"):
            for idx, printer_id in enumerate(printer_ids):
                packet = state["runtime"]["printer_stats"].get(printer_id, {})

                with ui.tab_panel(tab_refs[idx]):

                    # Keep a 30/70 split and scroll horizontally if min widths cannot fit.
                    with ui.row().classes("w-full no-wrap items-start gap-4").style("overflow-x: auto;"):

                        # LEFT PANEL (~30%, min width enforced)
                        with ui.column().classes("p-3 bg-grey-2 rounded").style("flex: 0 0 50%; min-width: 320px;"):
                            ui.label(f"Printer ID: {printer_id}").classes("text-subtitle1")

                            stats_rows = [
                                ("Machine Status", normalise_machine_status(packet.get("machine_status", "Unknown"))),
                                ("Print Status", normalise_printer_status(packet.get("print_status", "Unknown"))),
                                ("Progress", f"{packet.get('progress', 0)}%"),
                                ("File", packet.get("filename", "-")),
                                ("Nozzle Temp", f'{packet.get("nozzle_temp", "-")}°C'),
                                ("Bed Temp", f'{packet.get("bed_temp", "-")}°C'),
                                ("Chamber Temp", f'{packet.get("box_temp", "-")}°C'),
                                ("Fan Speed", packet.get("current_fan_speed", "-")),
                            ]

                            with ui.column().classes("w-full gap-1").style("overflow-x: auto;"):
                                for label, value in stats_rows:
                                    with ui.row().classes("w-full no-wrap items-start").style("min-width: 280px;"):
                                        ui.label(f"{label}:").classes("text-weight-medium")\
                                            .style("flex: 0 0 30%; min-width: 120px;")
                                        ui.label(str(value)).style(
                                            "flex: 1 1 auto; min-width: 160px; overflow-x: auto; white-space: nowrap;"
                                        )

                        # RIGHT PANEL (remaining width, min width enforced)
                        with ui.column().classes("p-3").style("flex: 1 1 auto; min-width: 520px;"):
                            ui.label("Live SDCP Data").classes("text-subtitle1")
                            # Add SDCP content here


@ui.refreshable
def render_webcam_panel():

    with ui.card().classes("w-full max-w-[1600px] mx-auto"):
        with ui.column().classes("w-full items-center gap-3"):
            ui.label("Live Webcam").classes("text-h6")

            webcam_state = state["runtime"].get("webcam", {})
            stream_url = webcam_state.get("stream_url", "")
            if stream_url:
                ui.image(stream_url).classes("w-full max-w-[600px] rounded mx-auto")
            else:
                ui.label("No webcam stream URL yet").classes("text-caption")

            if webcam_state.get("last_error"):
                ui.label(webcam_state["last_error"]).classes("text-negative text-caption")

            with ui.row().classes("items-center justify-center gap-2"):
                ui.button("Show Stream", on_click=show_stream).props("icon=videocam")
                ui.button("Hide Stream", on_click=hide_stream).props("icon=visibility_off")


def render_overview():
    render_overview_status()
    render_webcam_panel()

@ui.refreshable
def render_wizard():
    cfg = state["config"]
    global_cfg = cfg["global"]
    spoolman_cfg = cfg["spoolman"]
    notifications_cfg = cfg["notifications"]
    tags_cfg = notifications_cfg["tags"]
    
    with ui.row().classes("w-full justify-center"):
        with ui.column().classes("w-full max-w-[1000px]"):
            with ui.expansion("Global", icon="settings", value=True).classes("w-full"):
                with ui.grid(columns=1).classes("w-full"):
                    ui.select(
                        ["DEBUG", "INFO", "WARNING", "ERROR"],
                        label="Log Level",
                        value=global_cfg.get("log_level", "INFO"),
                        on_change=lambda e: set_key(global_cfg, "log_level", e.value),
                    )
                    ui.input(
                        "Watch Folder",
                        value=cfg["printers"][0].get("watch_folder", ""),
                        on_change=lambda e: set_key(cfg["printers"][0], "watch_folder", e.value),
                    )
                    ui.switch(
                        "Always Running",
                        value=bool(global_cfg.get("always_running", False)),
                        on_change=lambda e: set_key(global_cfg, "always_running", bool(e.value)),
                    )
                    ui.switch(
                        "Delete After Print",
                        value=bool(global_cfg.get("delete_after_print", True)),
                        on_change=lambda e: set_key(global_cfg, "delete_after_print", bool(e.value)),
                    )
                    ui.switch(
                        "Log Timestamps",
                        value=bool(global_cfg.get("log_timestamps", True)),
                        on_change=lambda e: set_key(global_cfg, "log_timestamps", bool(e.value)),
                    )
                    ui.switch(
                        "Hide One Time Terminal",
                        value=bool(global_cfg.get("hide_one_time_mode_terminal", False)),
                        on_change=lambda e: set_key(global_cfg, "hide_one_time_mode_terminal", bool(e.value)),
                    )

            with ui.expansion("Spoolman", icon="hub", value=False).classes("w-full"):
                with ui.grid(columns=1).classes("w-full"):
                    ui.switch(
                        "Enabled",
                        value=bool(spoolman_cfg.get("enabled", True)),
                        on_change=lambda e: set_key(spoolman_cfg, "enabled", bool(e.value)),
                    )
                    ui.input(
                        "URL",
                        value=spoolman_cfg.get("url", ""),
                        on_change=lambda e: set_key(spoolman_cfg, "url", e.value),
                    )
                    ui.input(
                        "Fallback URL",
                        value=spoolman_cfg.get("fallback_url", ""),
                        on_change=lambda e: set_key(spoolman_cfg, "fallback_url", e.value),
                    )

            with ui.expansion("Notifications", icon="notifications", value=False).classes("w-full"):
                with ui.grid(columns=1).classes("w-full"):
                    ui.switch(
                        "Enabled",
                        value=bool(notifications_cfg.get("enabled", True)),
                        on_change=lambda e: set_key(notifications_cfg, "enabled", bool(e.value)),
                    )
                    ui.input(
                        "Apprise URL",
                        value=notifications_cfg.get("apprise_url", ""),
                        on_change=lambda e: set_key(notifications_cfg, "apprise_url", e.value),
                    )
                    ui.input(
                        "Apprise Config",
                        value=notifications_cfg.get("apprise_config", "apprise"),
                        on_change=lambda e: set_key(notifications_cfg, "apprise_config", e.value),
                    )
                    ui.input(
                        "Custom Tag",
                        value=tags_cfg.get("custom", "spooler"),
                        on_change=lambda e: set_key(tags_cfg, "custom", e.value),
                    )
                    ui.input(
                        "Spoolman Tag",
                        value=tags_cfg.get("spoolman", "spoolman"),
                        on_change=lambda e: set_key(tags_cfg, "spoolman", e.value),
                    )

            with ui.expansion("Printers", icon="print", value=False).classes("w-full"):
                ui.button("Add Printer", on_click=add_printer).props("icon=add")
                for idx, printer in enumerate(cfg["printers"]):
                    with ui.card().classes("w-full"):
                        with ui.row().classes("items-center"):
                            ui.label(f"Printer {idx + 1}").classes("text-subtitle1")
                            if len(cfg["printers"]) > 1:
                                ui.button(
                                    "Remove",
                                    on_click=lambda _, i=idx: remove_printer(i),
                                ).props("color=negative flat")
                        with ui.grid(columns=2).classes("w-full"):
                            ui.input(
                                "ID",
                                value=printer.get("id", ""),
                                on_change=lambda e, p=printer: set_key(p, "id", e.value),
                            )
                            ui.input(
                                "Name",
                                value=printer.get("name", ""),
                                on_change=lambda e, p=printer: set_key(p, "name", e.value),
                            )
                            ui.input(
                                "SDCP WS URL",
                                value=printer.get("sdcp_ws_url", ""),
                                on_change=lambda e, p=printer: set_key(p, "sdcp_ws_url", e.value),
                            )
                            ui.input(
                                "Watch Folder",
                                value=printer.get("watch_folder", ""),
                                on_change=lambda e, p=printer: set_key(p, "watch_folder", e.value),
                            )
                            ui.switch(
                                "Enabled",
                                value=bool(printer.get("enabled", True)),
                                on_change=lambda e, p=printer: set_key(p, "enabled", bool(e.value)),
                            )
                            ui.switch(
                                "Delete After Print",
                                value=bool(printer.get("delete_after_print", True)),
                                on_change=lambda e, p=printer: set_key(p, "delete_after_print", bool(e.value)),
                            )

            with ui.expansion("Devices", icon="memory", value=False).classes("w-full"):
                ui.button("Add Device", on_click=add_device).props("icon=add")
                for idx, device in enumerate(cfg["devices"]):
                    connection = device["connection"]
                    with ui.card().classes("w-full"):
                        with ui.row().classes("items-center"):
                            ui.label(f"Device {idx + 1}").classes("text-subtitle1")
                            ui.button(
                                "Remove",
                                on_click=lambda _, i=idx: remove_device(i),
                            ).props("color=negative flat")
                        with ui.grid(columns=2).classes("w-full"):
                            ui.input(
                                "Config Device ID",
                                value=device.get("id", ""),
                                on_change=lambda e, d=device: set_key(d, "id", e.value),
                            )
                            ui.input(
                                "Device Type",
                                value=device.get("device_type", "airpurifier"),
                                on_change=lambda e, d=device: set_key(d, "device_type", e.value),
                            )
                            ui.input(
                                "Model",
                                value=device.get("model", ""),
                                on_change=lambda e, d=device: set_key(d, "model", e.value),
                            )
                            ui.switch(
                                "Always On",
                                value=bool(device.get("always_on", False)),
                                on_change=lambda e, d=device: set_key(d, "always_on", bool(e.value)),
                            )
                            ui.input(
                                "Tuya Device ID",
                                value=connection.get("device_id", ""),
                                on_change=lambda e, c=connection: set_key(c, "device_id", e.value),
                            )
                            ui.input(
                                "Tuya Local Key",
                                value=connection.get("local_key", ""),
                                password=True,
                                password_toggle_button=True,
                                on_change=lambda e, c=connection: set_key(c, "local_key", e.value),
                            )
                            ui.input(
                                "IP",
                                value=connection.get("ip", "Auto"),
                                on_change=lambda e, c=connection: set_key(c, "ip", e.value),
                            )

            with ui.expansion("Assignments", icon="device_hub", value=False).classes("w-full"):
                ui.button("Add Assignment", on_click=add_assignment).props("icon=add")
                for idx, assignment in enumerate(cfg["assignments"]):
                    policy = assignment["policy"]
                    with ui.card().classes("w-full"):
                        with ui.row().classes("items-center"):
                            ui.label(f"Assignment {idx + 1}").classes("text-subtitle1")
                            ui.button(
                                "Remove",
                                on_click=lambda _, i=idx: remove_assignment(i),
                            ).props("color=negative flat")
                        with ui.grid(columns=2).classes("w-full"):
                            ui.input(
                                "Device ID",
                                value=assignment.get("device_id", ""),
                                on_change=lambda e, a=assignment: set_key(a, "device_id", e.value),
                            )
                            ui.input(
                                "Printer IDs (comma separated)",
                                value=",".join(assignment.get("printer_ids", [])),
                                on_change=lambda e, a=assignment: set_key(a, "printer_ids", parse_csv(e.value)),
                            )
                            ui.switch(
                                "Turn On When Any Printing",
                                value=bool(policy.get("turn_on_when_any_printing", True)),
                                on_change=lambda e, p=policy: set_key(p, "turn_on_when_any_printing", bool(e.value)),
                            )
                            ui.switch(
                                "Turn Off When All Idle",
                                value=bool(policy.get("turn_off_when_all_idle", True)),
                                on_change=lambda e, p=policy: set_key(p, "turn_off_when_all_idle", bool(e.value)),
                            )
                            ui.number(
                                "Idle Grace Seconds",
                                value=policy.get("idle_grace_seconds", 180),
                                min=0,
                                step=1,
                                on_change=lambda e, p=policy: set_int_key(p, "idle_grace_seconds", e.value),
                            )


@ui.refreshable
def render_controls():
    ui.label("Device Controls").classes("text-h6")

    device_states = state["runtime"].get("device_states", [])
    if not device_states:
        ui.label("No live device state from daemon yet.")

    for entry in device_states:
        if not isinstance(entry, dict):
            continue

        name = entry.get("name", "device")
        meta = entry.get("meta", {}) if isinstance(entry.get("meta"), dict) else {}
        status = entry.get("state", {}) if isinstance(entry.get("state"), dict) else {}

        with ui.card().classes("w-full"):
            ui.label(f"{name}").classes("text-subtitle1")
            with ui.grid(columns=2).classes("w-full"):
                ui.label(f"Connected: {entry.get('connected', False)}")
                ui.label(f"Model: {meta.get('model', '-')}")
                ui.label(f"Power: {status.get('power', '-')}")
                ui.label(f"Mode: {status.get('mode', '-')}")
                ui.label(f"Fan Speed: {status.get('fan_speed', '-')}")
                ui.label(f"Filter Life: {status.get('filter_life', '-')}")

            if name == "airpurifier":
                with ui.row().classes("w-full"):
                    ui.button("Turn On", on_click=lambda: send_device_command("turn_on")).props("color=positive")
                    ui.button("Turn Off", on_click=lambda: send_device_command("turn_off")).props("color=negative")
                    ui.button("Sleep Mode", on_click=lambda: send_device_command("sleep_mode_on"))
                    ui.button("Manual Mode", on_click=lambda: send_device_command("sleep_mode_off"))

                with ui.row().classes("w-full"):
                    ui.button("Fan Low", on_click=lambda: send_device_command("set_fan_speed", "low"))
                    ui.button("Fan Mid", on_click=lambda: send_device_command("set_fan_speed", "mid"))
                    ui.button("Fan High", on_click=lambda: send_device_command("set_fan_speed", "high"))

    ui.separator()
    ui.label("SDCP Command Controls").classes("text-h6")
    with ui.card().classes("w-full"):
        with ui.grid(columns=2).classes("w-full"):
            ui.input(
                "Cmd",
                value=state["sdcp_form"]["cmd"],
                on_change=lambda e: set_key(state["sdcp_form"], "cmd", e.value),
            )
            ui.input(
                "Machine ID (optional)",
                value=state["sdcp_form"]["machine_id"],
                on_change=lambda e: set_key(state["sdcp_form"], "machine_id", e.value),
            )
            ui.input(
                "Topic (optional, overrides machine id)",
                value=state["sdcp_form"]["topic"],
                on_change=lambda e: set_key(state["sdcp_form"], "topic", e.value),
            )
            ui.input(
                "Data JSON",
                value=state["sdcp_form"]["data_json"],
                on_change=lambda e: set_key(state["sdcp_form"], "data_json", e.value),
            )

        ui.button("Send SDCP Command", on_click=send_sdcp_form_command).props("icon=send color=primary")

    with ui.card().classes("w-full"):
        ui.label("Raw SDCP Payload (advanced)").classes("text-subtitle1")
        ui.textarea(
            value=state["sdcp_form"]["raw_payload"],
            on_change=lambda e: set_key(state["sdcp_form"], "raw_payload", e.value),
        ).props("autogrow").classes("w-full")
        ui.button("Send Raw Payload", on_click=send_sdcp_raw_payload).props("icon=send color=primary")

    feedback = list(state["runtime"]["control_feedback"])
    if feedback:
        ui.separator()
        ui.label("Latest Control Results").classes("text-h6")
        with ui.card().classes("w-full"):
            for item in feedback[:10]:
                status = "OK" if item.get("ok") else "ERROR"
                message = item.get("message") or item.get("error") or ""
                ui.label(f"[{status}] {item.get('type', 'control')}: {message}")


@ui.refreshable
def render_logs():
    ui.label("Live Logs").classes("text-h6")
    with ui.card().classes("w-full"):
        ui.textarea(value="\n".join(state["runtime"]["logs"]))\
            .props("readonly autogrow")\
            .classes("w-full")

@ui.refreshable
def footer_content():
    connected = state["runtime"]["connected"]

    color = 'green' if connected else 'red'
    text = 'Connected' if connected else 'Disconnected'

    with ui.row().classes('items-center gap-2'):
        ui.icon('circle').classes(f'text-{color} text-sm')
        ui.label(f'Spooler © 2026 — {text}').classes('text-caption')
        ui.label(" | ").classes("text-caption")
        ui.label("Printers").classes("text-caption")
        ui.label(str(len(state["config"].get("printers", [])))).classes("text-caption")
        ui.label(" | ").classes("text-caption")
        ui.label("Devices").classes("text-caption")
        ui.label(str(len(state["config"].get("devices", [])))).classes("text-caption")
        ui.label(" | ").classes("text-caption")
        ui.label("Assignments").classes("text-caption")
        ui.label(str(len(state["config"].get("assignments", [])))).classes("text-caption")


    #     ui.label("Forwarder").classes("text-h6")
    #     status = "Connected" if state["runtime"]["connected"] else "Disconnected"
    #     ui.label(status)
    #     if state["runtime"]["last_error"]:
    #         ui.label(state["runtime"]["last_error"]).classes("text-caption")

    # with ui.card().classes("w-64"):
    #     ui.label("Printers").classes("text-h6")
    #     ui.label(str(len(cfg.get("printers", []))))

    # with ui.card().classes("w-64"):
    #     ui.label("Devices").classes("text-h6")
    #     ui.label(str(len(cfg.get("devices", []))))

    # with ui.card().classes("w-64"):
    #     ui.label("Assignments").classes("text-h6")
    #     ui.label(str(len(cfg.get("assignments", []))))


with ui.header(elevated=True):
    ui.label("Spooler").classes("text-h2")
    ui.label("Centauri Carbon - Spoolman - Orcaslicer Bridge").classes("text-h8")
    ui.space()
    with ui.tabs().classes("w-full, justify-start") as tabs:
        overview_tab = ui.tab("Overview", icon="dashboard")
        controls_tab = ui.tab("Controls", icon="tune")
        logs_tab = ui.tab("Logs", icon="subject")
        wizard_tab = ui.tab("Settings", icon="list_alt")
        raw_tab = ui.tab("Raw YAML", icon="code")




with ui.tab_panels(tabs, value=overview_tab).classes("w-full"):
    with ui.tab_panel(overview_tab):
        render_overview()

    with ui.tab_panel(controls_tab):
        render_controls()

    with ui.tab_panel(logs_tab):
        render_logs()

    with ui.tab_panel(wizard_tab):
        render_wizard()

    with ui.tab_panel(raw_tab):
        ui.label("Raw YAML Editor").classes("text-subtitle1")
        raw_yaml_editor = ui.textarea().props("autogrow").classes("w-full")
        with ui.row():
            ui.button("Sync From Form", on_click=sync_editor_from_state).props("icon=download")
            ui.button("Apply To Form", on_click=apply_editor_yaml).props("icon=upload")
            ui.button("Save YAML", on_click=save_clicked).props("icon=save color=positive")

with ui.footer().classes('bg-grey-7 text-white p-2'):
    footer_content()

sync_editor_from_state()

ui.timer(1.0, lambda: (render_overview_status.refresh(), render_controls.refresh(), render_logs.refresh(), footer_content.refresh()))
ui.timer(0.1, ensure_background_tasks, once=True)
ui.timer(3.0, ensure_background_tasks)

ui.run(title="Spooler Web GUI", host="0.0.0.0", port=8949, reload=False, show=False)

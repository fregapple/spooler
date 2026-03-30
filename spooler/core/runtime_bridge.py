import asyncio

from sdcp.forwarder import forward
from utils.colors import DEVICE, SDCP


async def _read_airpurifier_state(device):
    def _read():
        state = {"device_type": "airpurifier"}
        state["power"] = bool(device.get_power())
        state["mode"] = device.get_mode()
        state["fan_speed"] = device.get_fan_speed()
        state["led"] = bool(device.get_led())
        state["filter_life"] = device.check_filter_life()
        state["filter_time"] = device.get_filter_time()
        return state

    return await asyncio.to_thread(_read)


async def collect_device_states(devices):
    states = []

    for name, device in devices.__dict__.items():
        if device is None:
            continue

        payload = {"name": name}

        try:
            payload["meta"] = device.to_dict()
        except Exception:
            payload["meta"] = {"type": name}

        try:
            if name == "airpurifier":
                payload["state"] = await _read_airpurifier_state(device)
            else:
                payload["state"] = {"status": "unknown"}
            payload["connected"] = True
        except Exception as exc:
            payload["state"] = {"error": str(exc)}
            payload["connected"] = False

        states.append(payload)

    return states


async def publish_device_state_snapshot(devices, log):
    try:
        states = await collect_device_states(devices)
        await forward("device_state", {"devices": states})
    except Exception as exc:
        log.warn(DEVICE, f"Failed to publish device state: {exc}")


async def device_state_publisher(devices, log, interval_seconds=5):
    while True:
        await publish_device_state_snapshot(devices, log)
        await asyncio.sleep(interval_seconds)


async def execute_device_command(devices, command, log):
    device_type = str(command.get("device_type", "")).strip().lower()
    action = str(command.get("action", "")).strip().lower()
    value = command.get("value")

    if not device_type:
        return {"ok": False, "error": "device_type is required"}

    device = getattr(devices, device_type, None)
    if device is None:
        return {"ok": False, "error": f"Device '{device_type}' is not available"}

    def _run_action():
        if action == "turn_on":
            device.turn_on()
        elif action == "turn_off":
            device.turn_off()
        elif action == "sleep_mode_on":
            device.sleep_mode_on()
        elif action == "sleep_mode_off":
            device.sleep_mode_off()
        elif action == "set_fan_speed":
            device.set_fan_speed(str(value or "mid"))
        elif action == "led_on":
            device.led_on()
        elif action == "led_off":
            device.led_off()
        else:
            raise ValueError(
                "Unsupported action. Use turn_on, turn_off, sleep_mode_on, "
                "sleep_mode_off, set_fan_speed, led_on, or led_off."
            )

    try:
        await asyncio.to_thread(_run_action)
        log.info(DEVICE, f"WebGUI command executed: {device_type}.{action}")
        return {"ok": True, "message": f"Executed {device_type}.{action}"}
    except Exception as exc:
        log.error(DEVICE, f"WebGUI device command failed: {exc}")
        return {"ok": False, "error": str(exc)}


async def control_loop(control_queue, devices, sdcp_command_queue, log):
    while True:
        message = await control_queue.get()

        if not isinstance(message, dict):
            continue

        message_type = message.get("type")
        payload = message.get("data", {})

        if message_type == "device_command":
            result = await execute_device_command(devices, payload, log)
            await forward("control_result", {"type": "device_command", **result})

            if result.get("ok"):
                await publish_device_state_snapshot(devices, log)

        elif message_type == "sdcp_command":
            await sdcp_command_queue.put(payload)
            await forward(
                "control_result",
                {"type": "sdcp_command", "ok": True, "message": "SDCP command queued"},
            )
            log.info(SDCP, "Queued SDCP command from WebGUI")

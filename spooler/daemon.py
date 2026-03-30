import asyncio

from core.config import Config
from core.device_loader import load_devices
from core.initial_scan import initial_folder_scan
from core.logger import Logger
from core.runtime_bridge import (
    control_loop,
    device_state_publisher,
    publish_device_state_snapshot,
)
from sdcp.forwarder import forward, get_control_queue, start_forwarder
from sdcp.listener import sdcp_listener
from spoolman.manager import refresh_spool_cache
from utils.colors import CONFIG, MAIN
from watchers.folder_watcher import start_folder_watcher


async def main_async():
    # Bootstrap logger for early config errors
    bootstrap_log = Logger(level="INFO", use_timestamp=True)

    # Start forwarder
    await start_forwarder()
    control_queue = get_control_queue()
    sdcp_command_queue = asyncio.Queue()

    # Load config
    try:
        config = Config(logger=bootstrap_log)
        await forward("config", config.to_dict())

    except Exception as e:
        bootstrap_log.error(CONFIG, str(e))
        return

    # Main logger
    log = Logger(level=config.log_level, use_timestamp=config.log_timestamps)
    log.info(MAIN, "Configuration loaded successfully")
    log.info(MAIN, "Starting daemon ...")

    # Load devices
    device_dicts = []
    devices = load_devices(config, log)
    for name, device in devices.__dict__.items():
        if device is not None:
            device_dicts.append(device.to_dict())
    await forward("devices", device_dicts)

    # Publish an initial device state snapshot for GUI clients.
    await publish_device_state_snapshot(devices, log)

    # Load spool cache
    refresh_spool_cache(config, log)

    # Initial scan of G-code folder
    initial_folder_scan(config, log)

    # Start folder watcher
    observer = start_folder_watcher(config, log)

    # Start SDCP listener
    sdcp_task = asyncio.create_task(sdcp_listener(config, log, devices, command_queue=sdcp_command_queue))

    # Start periodic device-state updates and control handling
    device_state_task = asyncio.create_task(device_state_publisher(devices, log))
    control_task = asyncio.create_task(control_loop(control_queue, devices, sdcp_command_queue, log))

    # Wait for shutdown
    await config.shutdown_event.wait()

    log.info(MAIN, "Shutdown event received, stopping services ...")

    # Stop folder watcher
    observer.stop()
    observer.join()

    # Stop SDCP listener
    sdcp_task.cancel()
    device_state_task.cancel()
    control_task.cancel()
    try:
        await sdcp_task
    except Exception:
        pass

    try:
        await device_state_task
    except Exception:
        pass

    try:
        await control_task
    except Exception:
        pass

    log.info(MAIN, "Daemon exiting cleanly")


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Interrupted by user")

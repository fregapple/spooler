import asyncio
from core.config import Config
from core.logger import Logger
from utils.colors import MAIN, CONFIG
from core.device_loader import load_devices
from core.initial_scan import initial_folder_scan
from watchers.folder_watcher import start_folder_watcher
from spoolman.manager import refresh_spool_cache
from sdcp.listener import sdcp_listener
from sdcp.forwarder import forward, start_forwarder


async def main_async():
    # Bootstrap logger for early config errors
    bootstrap_log = Logger(level="INFO", use_timestamp=True)

    # Start forwarder
    await start_forwarder()

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


    # Load spool cache
    refresh_spool_cache(config, log)

    # Initial scan of G-code folder
    initial_folder_scan(config, log)

    # Start folder watcher
    observer = start_folder_watcher(config, log)

    # Start SDCP listener
    sdcp_task = asyncio.create_task(sdcp_listener(config, log, devices))

    # Wait for shutdown
    await config.shutdown_event.wait()

    log.info(MAIN, "Shutdown event received, stopping services ...")

    # Stop folder watcher
    observer.stop()
    observer.join()

    # Stop SDCP listener
    sdcp_task.cancel()
    try:
        await sdcp_task
    except:
        pass

    log.info(MAIN, "Daemon exiting cleanly")


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Interrupted by user")

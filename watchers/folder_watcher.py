# watchers/folder_watcher.py
from watchdog.observers import Observer
from watchers.gcode_handler import GcodeHandler
from utils.colors import WATCH

def start_folder_watcher(config, log):
    handler = GcodeHandler(log, config.watch_folder)
    observer = Observer()
    observer.schedule(handler, config.watch_folder, recursive=False)
    observer.start()

    log.info(WATCH, f"Folder watcher started on {config.watch_folder}")
    return observer
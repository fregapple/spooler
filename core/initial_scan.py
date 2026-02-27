# watchers/initial_scan.py
import os
from utils.file_wait import wait_for_file_complete
from utils.colors import WATCH
from gcode.parser import parse_gcode_metadata
from core.state import pending_jobs

def initial_folder_scan(config, log):
    log.info(WATCH, "Performing initial folder scan...")

    for filename in os.listdir(config.watch_folder):
        if not filename.lower().endswith(".gcode"):
            continue

        path = os.path.join(config.watch_folder, filename)
        log.info(WATCH, f"Found existing G-code: {filename}")

        wait_for_file_complete(path)

        meta = parse_gcode_metadata(path)
        pending_jobs[filename] = meta
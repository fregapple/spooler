# watchers/gcode_handler.py
import os

from core.state import pending_jobs
from gcode.parser import parse_gcode_metadata
from utils.colors import WATCH
from utils.file_wait import wait_for_file_complete
from watchdog.events import FileSystemEventHandler


class GcodeHandler(FileSystemEventHandler):
    def __init__(self, log, watch_folder):
        super().__init__()
        self.log = log
        self.watch_folder = watch_folder

    def on_created(self, event):
        if event.is_directory:
            return

        if not event.src_path.lower().endswith(".gcode"):
            return

        filename = os.path.basename(event.src_path)

        wait_for_file_complete(event.src_path)
        self.log.info(WATCH, f"New G-code detected: {filename}")

        meta = parse_gcode_metadata(event.src_path)
        pending_jobs[filename] = meta

        self.log.info(WATCH, f"Parsed metadata: {meta}")

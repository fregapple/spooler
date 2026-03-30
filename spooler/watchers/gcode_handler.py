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
        self._processed_mtimes = {}

    def _maybe_process_path(self, path):
        if not path.lower().endswith(".gcode"):
            return

        filename = os.path.basename(path)
        if not os.path.exists(path):
            return

        mtime = os.path.getmtime(path)
        if self._processed_mtimes.get(path) == mtime:
            return

        wait_for_file_complete(path)
        self.log.info(WATCH, f"New/updated G-code detected: {filename}")

        meta = parse_gcode_metadata(path)
        pending_jobs[filename] = meta
        self._processed_mtimes[path] = mtime

        self.log.info(WATCH, f"Parsed metadata: {meta}")

    def on_created(self, event):
        if event.is_directory:
            return
        self._maybe_process_path(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._maybe_process_path(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        self._maybe_process_path(event.dest_path)

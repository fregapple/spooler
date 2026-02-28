import asyncio
import os
import re
from datetime import datetime
from pathlib import Path

from sdcp.forwarder import forward
from utils.colors import LOG_DEBUG, LOG_ERROR, LOG_INFO, LOG_WARN, RESET

ANSI_ESCAPE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
BASE_DIR = Path(__file__).parent.parent
LOG_PATH = BASE_DIR / "logs" / "daemon.log"

class Logger:
    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARN": 30,
        "ERROR": 40
    }

    COLORS = {
        "DEBUG": LOG_DEBUG,
        "INFO": LOG_INFO,
        "WARN": LOG_WARN,
        "ERROR": LOG_ERROR
    }

    def __init__(self, 
                 level="INFO", 
                 use_timestamp=True,
                 log_to_file=True,
                 file_path=LOG_PATH,
                 max_size_mb=5,
                 max_backups=2):
        
        self.level = self.LEVELS.get(level.upper(), 20)
        self.use_timestamp = use_timestamp

        self.log_to_file = log_to_file
        self.file_path = Path(file_path)
        self.max_size = max_size_mb * 1024 * 1024
        self.max_backups = max_backups
    
    def _should_log(self, level):
        return self.LEVELS[level] >= self.level
    
    def _format(self, level, tag, message):
        color = self.COLORS[level]
        colored_message = f"{color}{message}{RESET}" if color else message

        if self.use_timestamp:
            ts = datetime.now().strftime("%H:%M:%S")
            return f"{ts} {tag} {colored_message}"
        return f"{tag} {colored_message}"
    
    def _forward_log(self, level, tag, message):
        try:
            asyncio.create_task(forward("log", {
                "level": level,
                "tag": tag,
                "message": message
            }))
        except RuntimeError:
            pass

    def _rotate_if_needed(self):
        if not self.file_path.exists():
            return
        
        if self.file_path.stat().st_size < self.max_size:
            return
        
        for i in range(self.max_backups, 0, -1):
            old = self.file_path.with_suffix(self.file_path.suffix + f".{i}")
            older = self.file_path.with_suffix(self.file_path.suffix + F".{i+1}")
            if old.exists():
                if i == self.max_backups:
                    old.unlink()
                else:
                    old.rename(older)

        self.file_path.rename(self.file_path.with_suffix(self.file_path.suffix + ".1"))

    def _write_to_file(self, text):
        if not self.log_to_file:
            return

        if not Path.exists(BASE_DIR / "logs"):
            os.makedirs(BASE_DIR / "logs", exist_ok=True)
        
        clean_text = ANSI_ESCAPE.sub('', text)
    
        self._rotate_if_needed()

        with self.file_path.open("a", encoding="utf-8") as f:
            f.write(clean_text + "\n")

    def debug(self, tag, message):
        if self._should_log("DEBUG"):
            text = self._format("DEBUG", tag, message)
            print(text)
            self._write_to_file(text)
            self._forward_log("DEBUG", tag, message)

    def info(self, tag,message):
        if self._should_log("INFO"):
            text = self._format("INFO", tag, message)
            print(text)
            self._write_to_file(text)
            self._forward_log("INFO", tag, message)

    def warn(self, tag, message):
        if self._should_log("WARN"):
            text = self._format("WARN", tag, message)
            print(text)
            self._write_to_file(text)
            self._forward_log("WARN", tag, message)

    def error(self, tag, message):
        if self._should_log("ERROR"):
            text = self._format("ERROR", tag, message)
            print(text)
            self._write_to_file(text)
            self._forward_log("ERROR", tag, message)
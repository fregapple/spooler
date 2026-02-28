import os
import time

# -----------------------------
# FILE WRITE WAIT
# -----------------------------
"""
This is needed to allow the GCODE file is completely created before reading it. Otherwise the daemon will load a partially created or empty gcode. Which will most-likely be missing the required information
"""
def wait_for_file_complete(path, timeout=5):
    last_size = -1
    for _ in range(timeout * 10):
        try:
            size = os.path.getsize(path)
        except FileNotFoundError:
            size = -1

        if size == last_size and size > 0:
            return True

        last_size = size
        time.sleep(0.1)

    return False
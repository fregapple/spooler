import shutil
import sys
import os
import json
import subprocess

# OrcaSlicer passes the G-code file path as the first argument
gcode_path = sys.argv[1]



# ------------------------------
# One Time Run Mode
# ------------------------------
"""
Use these configs if you want to use One Time Run Mode. Leave as None if you don't want to use it.
"""
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

LOCAL_VENV = os.path.join(SCRIPT_DIR, "venv")

DAEMON_FOLDER = SCRIPT_DIR  # <-- change to your actual daemon file location

CONFIG_PATH = os.path.join(DAEMON_FOLDER, "config.json") # 

# Your daemon's watch folder
WATCH_FOLDER = os.path.join(DAEMON_FOLDER, "watch")      

# Ensure folder exists
os.makedirs(WATCH_FOLDER, exist_ok=True)

# Resolve final output filename

output_name = os.environ.get('SLIC3R_PP_OUTPUT_NAME')

# Copy file: Atomic copy and then replace to help ensure daemon gets full file.

dest = os.path.join(WATCH_FOLDER, os.path.basename(output_name))
temp_dest = dest + ".tmp"
shutil.copy2(gcode_path, temp_dest)
os.replace(temp_dest, dest)

print(f"[POST] Copied {gcode_path} → {dest}")


if CONFIG_PATH is not None:
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)

    if not cfg.get("always_running", True):

        env = os.environ.copy()
        env["AGENT_VENV"] = LOCAL_VENV

        print("[POST] Launching daemon in one-time mode ... ")

        if os.name == "nt":
            if cfg["hide_one_time_mode_terminal"]:
                input(1)
                subprocess.Popen([DAEMON_FOLDER + r"\run.bat"], shell=True, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([DAEMON_FOLDER + r"\run.bat"], shell=True, env=env)
        else:
            subprocess.Popen(["bash", DAEMON_FOLDER + r"\run.sh"], env=env)


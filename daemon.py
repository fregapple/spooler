import asyncio
import json
import os
import time
import re
import websockets
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# -----------------------------
# CONFIG LOADING
# -----------------------------
def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

config = load_config()

SDCP_WS_URL = config["sdcp_ws_url"]
WATCH_FOLDER = config["watch_folder"]
SPOOLMAN_URL = config["spoolman_url"]
SPOOLMAN_LOCAL_URL = config["spoolman_local_url"]
DELETE_AFTER_PRINT = config.get("delete_after_print", True)


# -----------------------------
# GLOBAL STATE
# -----------------------------
pending_jobs = {}   # filename → metadata
spool_cache = []    # list of spools from Spoolman
shutdown_event = asyncio.Event()


# -----------------------------
# SPOOLMAN API (v1)
# -----------------------------
def refresh_spool_cache():
    """
    Ensuring we always have the latest spool information
    """
    global spool_cache
    try:
        r = requests.get(f"{SPOOLMAN_URL}/api/v1/spool")
        r.raise_for_status()
        spool_cache = r.json()
        print(f"[SPOOLMAN] Loaded {len(spool_cache)} spools")
    except:
        try:
            r = requests.get(f"{SPOOLMAN_URL}/api/v1/spool")
            r.raise_for_status()
            spool_cache = r.json()
            print(f"[SPOOLMAN] Loaded {len(spool_cache)} spools")
        except Exception as e:
            print(f"[SPOOLMAN] Failed to load spools: {e}")


def update_spoolman(spool_id, filament_g):
    """
    This is what we use to actually deduct filament from a spool.
    after we have gained our spool_id by matching in find_spool_for_preset it will then deduct the filament_g that we obtained from the GCODE.
    """
    url = f"{SPOOLMAN_URL}/api/v1/spool/{spool_id}/use"
    payload = {"use_weight": filament_g}

    try:
        r = requests.put(url, json=payload)
        r.raise_for_status()
        print(f"[SPOOLMAN] Subtracted {filament_g}g from spool {spool_id}")
    except Exception as e:
        print(f"[SPOOLMAN] Error updating spool: {e}")


# -----------------------------
# SPOOL MATCHING HELPERS
# -----------------------------
def split_preset_name(preset):
    """
    Expected format: 'Vendor - Material - Color'
    Returns (vendor, material, color) or (None, None, None) if invalid.
    """
    parts = [p.strip() for p in preset.split("-")]
    if len(parts) < 3:
        return None, None, None

    vendor = parts[0]
    material = parts[1]
    color = "-".join(parts[2:])  # in case color itself has dashes
    return vendor, material, color


def find_spool_for_preset(preset):
    """
    Multi-stage matching using a filament preset string.
    1. Exact vendor + material + color
    2. Vendor + color
    3. Color only
    """
    vendor, material, color = split_preset_name(preset)
    if not vendor or not material or not color:
        print(f"[MATCH] Invalid preset format: '{preset}'")
        return None

    vendor_l = vendor.lower()
    material_l = material.lower()
    color_l = color.lower()
    
    """
    I have made 3 options here. But I prefer the first and will do my best to always match to that over all else.
    Reason: We want to filter spoolman completely for when we may have a big inventory of spools from various manufactorers and / or different material types that share the same color name.
    
    EG ELEGOO - Yellow - PLA would match in the second and third options against ELEGOO - Yellow - PETG. Which really is not ideal. I may even refactor this and remove the other options in the future if I run into any issues.
    I just thought it would be best to have some back up options. That being said, if we setup our spools properly in both orca AND spoolman, than it will never be a problem.
    """
    # Exact match: vendor + material + color (color from 'color' or 'name')
    for spool in spool_cache:
        f = spool.get("filament", {})
        s_vendor = f.get("vendor", {}).get("name", "").lower()
        s_material = f.get("material", "").lower()
        s_color = f.get("name", "").lower()

        if s_vendor == vendor_l and s_material == material_l and s_color == color_l:
            return spool["id"]

    # Vendor + color
    for spool in spool_cache:
        s_vendor = spool.get("vendor", "").lower()
        s_color = (spool.get("color") or spool.get("name", "")).lower()

        if s_vendor == vendor_l and s_color == color_l:
            return spool["id"]

    # Color only
    for spool in spool_cache:
        s_color = (spool.get("color") or spool.get("name", "")).lower()
        if s_color == color_l:
            return spool["id"]

    return None
# -----------------------------
# INITIAL FOLDER SCAN
# -----------------------------
"""
Need for a race condition. So that if the file is already in the folder before the daemon starts, it can still load it into the metadata.
Thoughts are so that if for some reason the daemon restarts, it can regrab the information for the print.
"""

def initial_folder_scan():
    print("[WATCH] Performing initial folder scan ... ")
    for filename in os.listdir(WATCH_FOLDER):
        if filename.lower().endswith(".gcode"):
            path = os.path.join(WATCH_FOLDER, filename)
            print(f"[WATCH] Found existing G-code: {filename}")

            # Ensure file is complete

            wait_for_file_complete(path)

            meta = parse_gcode_metadata(path)
            pending_jobs[filename] = meta

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
# -----------------------------
# NORMALIZE FILAMENT USAGE
# -----------------------------

def normalize_filament_usage(filament_presets, filament_g_list):

    if len(filament_g_list) <= 1:
        return filament_presets, filament_g_list
    
    max_idx = max(range(len(filament_g_list)), key=lambda i: filament_g_list[i])
    max_val = filament_g_list[max_idx]

    # Gather all filaments under 1g to combine to 1 main filament.

    tiny_indices = [i for i, g in enumerate(filament_g_list) if g < 1.0 and i != max_idx]

    # If no tiny filaments, leave as-is

    if not tiny_indices:
        return filament_presets, filament_g_list
    
    # Sum tiny filaments

    tiny_sum = sum(filament_g_list[i] for i in tiny_indices)

    # Add them to largest filament

    filament_g_list[max_idx] += tiny_sum

    # Remove tiny entries from both lists

    for i in sorted(tiny_indices, reverse=True):
        del filament_g_list[i]
        del filament_presets[i]

    return filament_presets, filament_g_list

# -----------------------------
# GCODE PARSER
# -----------------------------
"""
The Gcode contains all the information we need outta the box
filament_settings_id - will provide a list of all filaments used in current project
filament used [g] - will provide a list that is determined by how many filaments it is using. I have noticed that it seems to be in the same order as filament_settings_id.
        That being said, just because it lists something doesn't mean it has a value attached. 
        EXAMPLE: 
            filament_settings_id = ["black", "yellow", "red"]
            filament used [g] = ["0.00", "10.00", "0.00"]
            
            In my findings this would mean that Yellow filament has used 10 grams of filament. This is the exact information we need to pass onto spoolman as long as the filament_settings_id is in the correct format which is highlighted in the readme."""
def parse_gcode_metadata(path):
    filament_presets = None
    filament_g_list = None

    with open(path, "r", errors="ignore") as f:
        for line in f:
            lower = line.lower()

            # --- FILAMENT PRESETS ---
            if "filament_settings_id" in lower and filament_presets is None:
                # Extract all quoted strings
                presets = re.findall(r'"([^"]+)"', line)
                if presets:
                    filament_presets = presets

            # --- FILAMENT USED [G] ---
            if "filament used [g]" in lower and filament_g_list is None:
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                if nums:
                    filament_g_list = [float(n) for n in nums]

            # stop early if both found
            if filament_g_list is not None and filament_presets is not None:
                break
    # Add any filaments < 1 and add them to the biggest filament. Helps when the purge line at the start of a print is a different color.. Yes, it is only 0.8g. But I want it to be close as we can as an estimate.      
    filament_presets, filament_g_list = normalize_filament_usage(filament_presets, filament_g_list)

    return {
        "filament_presets": filament_presets or [],
        "filament_g_list": filament_g_list or [],
        "path": path
    }


# -----------------------------
# FILE WATCHER
# -----------------------------
class GcodeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith(".gcode"):
            filename = os.path.basename(event.src_path)
            wait_for_file_complete(event.src_path)
            print(f"[WATCH] New G-code detected: {filename}")

            meta = parse_gcode_metadata(event.src_path)
            pending_jobs[filename] = meta

            print(f"[WATCH] Parsed metadata: {meta}")


def start_folder_watcher():
    observer = Observer()
    handler = GcodeHandler()
    observer.schedule(handler, WATCH_FOLDER, recursive=False)
    observer.start()
    print("[WATCH] Folder watcher started")
    return observer


# -----------------------------
# SDCP KEEP-ALIVE
# -----------------------------
"""
This keeps the daemon connected to the websocket, otherwise the printed closes the connection and we have to reconnect every minute give or take
"""
async def keepalive(ws):
    while True:
        try:
            await ws.send(json.dumps({"cmd": "get_state"}))
        except:
            return
        await asyncio.sleep(15)

# -----------------------------
# FAKE TEST PRINT
# -----------------------------

async def simulate_fake_print(print_active_ref, waiting_for_idle_ref, config):
    """
    Simulates a print start → print end → idle transition.
    This triggers your existing detection logic without needing a real print.
    """

    print("[TEST] Simulating fake print start")

    # Fake start packet
    current_status = 13
    filename = "FAKE_TEST_FILE.gcode"

    # Trigger your existing print-start logic
    print_active_ref[0] = True
    waiting_for_idle_ref[0] = False

    print("[SDCP] Print started detected via test packet")
    print(f"[SDCP] Filename reported: {filename}")

    # Simulate printing for a moment
    await asyncio.sleep(2)

    print("[TEST] Simulating fake print end")

    # Fake end packet
    current_status = 0  # or 1, doesn't matter for your logic

    print("[SDCP] Print ended or paused, resetting state")
    print_active_ref[0] = False
    waiting_for_idle_ref[0] = True

    # Simulate idle transition
    await asyncio.sleep(1)
    print("[SDCP] Printer is idle")

    if not config["always_running"]:
        print("[SDCP] One Time Mode: Exiting now (TEST)")
        return True  # signal shutdown

    waiting_for_idle_ref[0] = False
    return False


# -----------------------------
# SDCP WEBSOCKET LISTENER (STATUS-BASED)
# -----------------------------
async def sdcp_listener():
    last_status = None # Not currently in use, but could be useful if needed.
    print_active = False # This prevents repeating file checks
    waiting_for_idle = False  # This prevents early exit on "always_running" = False.
    print_active_ref = [False]
    waiting_for_idle_ref = [False]
    test_print = False # SET TO TRUE TO TEST THE PRINT EXIT CONDITON.

    while True:
        try:
            print("[SDCP] Connecting...")
            async with websockets.connect(SDCP_WS_URL) as ws:
                print("[SDCP] Connected")

                asyncio.create_task(keepalive(ws))

                # Calls a Test Print.
                if test_print:
                    should_exit = await simulate_fake_print(print_active_ref, waiting_for_idle_ref, config)
                    if should_exit:
                        shutdown_event.set()
                        return
                    
                async for msg in ws:
                    data = json.loads(msg)

                    # Only process status packets
                    if "Status" not in data:
                        continue

                    status_block = data["Status"]
                    printinfo = status_block.get("PrintInfo", {})

                    current_status = printinfo.get("Status")
                    filename = printinfo.get("Filename", "")

                    if current_status is None:
                        continue

                    # -----------------------------
                    # PRINT START DETECTION
                    # -----------------------------
                    if current_status == 13 and not print_active:
                        print_active = True
                        print(f"[SDCP] Print started detected via status transition")
                        print(f"[SDCP] Filename reported: {filename}")

                        shortname = os.path.basename(filename)

                        # Retry for race condition
                        if shortname not in pending_jobs:
                            print("[SDCP] No matching job yet, retrying...")

                            max_retries = 60  # 60 seconds
                            for attempt in range(max_retries):
                                await asyncio.sleep(1)

                                if shortname in pending_jobs:
                                    print(f"[SDCP] Match found after {attempt+1} seconds")
                                    break

                                if attempt % 10 == 0:
                                    print(f"[SDCP] Still waiting for metadata... ({attempt}/{max_retries})")

                        if shortname not in pending_jobs:
                            print(f"[SDCP] Still no matching job for '{shortname}' after full retry window, skipping")
                        else:
                            job = pending_jobs[shortname]
                            presets = job.get("filament_presets", [])
                            usage_list = job.get("filament_g_list", [])

                            print(f"[SDCP] Using metadata: presets={presets}, usage={usage_list}")

                            if not presets or not usage_list:
                                print(f"[ERROR] Missing filament metadata for {shortname}")
                            else:
                                refresh_spool_cache()

                                for preset, usage_g in zip(presets, usage_list):
                                    if usage_g <= 0:
                                        continue

                                    spool_id = find_spool_for_preset(preset)
                                    if not spool_id:
                                        print(f"[ERROR] No matching spool for preset '{preset}'")
                                        continue

                                    print(f"[INFO] Subtracting {usage_g}g from spool {spool_id} ({preset})")
                                    update_spoolman(spool_id, usage_g)

                            # Cleanup
                            if DELETE_AFTER_PRINT:
                                """
                                I prefer this setup as most of the time we just print it once and that is that. No need to keep so many duplicates.
                                Although, we can turn this off in the config, a use for that could be say: 
                                    We have "always_running": True and "delete_after_print": False, this would mean the file would stay in the folder and thus the metadata. We could then run a print again of the same GCODE from the printer itself
                                        and it would still subtract the filament from spoolman.
                                        
                                    This would be useful if we prefered to use the printers interface to do the printing or even when we use other interfaces like octoeverywhere, or we do a mix of both. deleting the file means we need to move the gcode 
                                        (manually or automatically with script) each time we print. I like this method as I have the pc here, but I can see pros for the other way also.
                                        
                                    Though, as I don't use the other way, I am not certain about how well it works when there are MANY GCODEs available. But as the daemon ensures to only use the settings of the matching GCODE file, then it should be okay.
                                        Infact it should be fine as it saves the metadata as a dict {{filename}: {metadata}}. 
                                    """
                                try:
                                    os.remove(job["path"])
                                    print(f"[CLEANUP] Deleted {job['path']}")
                                except Exception as e:
                                    print(f"[CLEANUP] Failed to delete: {e}")

                            del pending_jobs[shortname]

                    # -----------------------------
                    # PRINT END DETECTION
                    # -----------------------------
                    if current_status != 13 and print_active:
                        print("[SDCP] Print ended or paused, resetting state")
                        print_active = False
                        waiting_for_idle = True
                    
                    

                    if waiting_for_idle and current_status == 1:
                        print("[SDCP] Printer is idle")

                        if not config["always_running"]:
                            print("[SDCP] One Time Mode: Exiting now")
                            shutdown_event.set()
                            return
                        
                        waiting_for_idle = False

                        

                    last_status = current_status

                    

        except Exception as e:
            print(f"[SDCP] Connection error: {e}")
            print("[SDCP] Reconnecting in 3 seconds...")
            await asyncio.sleep(3)
# -----------------------------
# MAIN
# -----------------------------
async def main_async():
    refresh_spool_cache()
    observer = start_folder_watcher()

    initial_folder_scan()

    # Start SDCP listener
    sdcp_task = asyncio.create_task(sdcp_listener())

    # Wait for shutdown signal
    await shutdown_event.wait()

    print("[MAIN] Shutdown event received, stopping services...")

    # Stop folder watcher
    observer.stop()
    observer.join()

    # Cancel SDCP listener if still running
    sdcp_task.cancel()
    try:
        await sdcp_task
    except:
        pass

    print("[MAIN] Daemon exiting cleanly")

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("[MAIN] Interrupted by user")

if __name__ == "__main__":
    main()

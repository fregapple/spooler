import os
import re
from gcode.normalizer import normalize_filament_usage

def parse_gcode_metadata(path):
    """
    Extracts filament preset names and filament usage (grams) from a G-code file.
    Returns a dict with:
        - filament_presets: list[str]
        - filament_g_list: list[float]
        - path: str
    """

    filament_presets = None
    filament_g_list = None

    if not os.path.exists(path):
        return {"filament_presets": [], "filament_g_list": [], "path": path}

    with open(path, "r", errors="ignore") as f:
        for line in f:
            lower = line.lower()

            # --- FILAMENT PRESETS ---
            if "filament_settings_id" in lower and filament_presets is None:
                presets = re.findall(r'"([^"]+)"', line)
                if presets:
                    filament_presets = presets

            # --- FILAMENT USED [G] ---
            if "filament used [g]" in lower and filament_g_list is None:
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                if nums:
                    filament_g_list = [float(n) for n in nums]

            # Stop early if both found
            if filament_presets is not None and filament_g_list is not None:
                break

    # Normalize purge-line usage
    filament_presets, filament_g_list = normalize_filament_usage(
        filament_presets, filament_g_list
    )

    return {
        "filament_presets": filament_presets or [],
        "filament_g_list": filament_g_list or [],
        "path": path
    }
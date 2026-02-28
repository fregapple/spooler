import math

def parse_message(msg):
    """Return None if irrelevant, or a dict with parsed SDCP status."""
    if "Status" not in msg:
        return None

    status = msg["Status"]
    printinfo = status.get("PrintInfo", {})

    return {
        "machine_status": status.get("CurrentStatus"),
        "current_fan_speed": status.get("CurrentFanSpeed"),
        "nozzle_temp": round(status.get("TempOfNozzle"), 0),
        "bed_temp": round(status.get("TempOfHotbed"), 0),
        "box_temp": round(status.get("TempOfBox"), 0),
        "print_status": printinfo.get("Status"),
        "filename": printinfo.get("Filename", ""),
        "progress": printinfo.get("Progress", 0),
        "printinfo": printinfo
    }
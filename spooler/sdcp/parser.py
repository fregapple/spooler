def parse_message(msg):
    """Return None if irrelevant, or a dict with parsed SDCP status."""
    if "Status" not in msg:
        return None

    status = msg["Status"]
    printinfo = status.get("PrintInfo", {})

    return {
        "machine_status": status.get("CurrentStatus"),
        "current_fan_speed": status.get("CurrentFanSpeed"),
        "nozzle_temp": int(round(status.get("TempOfNozzle"))),
        "bed_temp": int(round(status.get("TempOfHotbed"))),
        "box_temp": int(round(status.get("TempOfBox"))),
        "print_status": printinfo.get("Status"),
        "filename": printinfo.get("Filename", ""),
        "progress": printinfo.get("Progress", 0),
        "printinfo": printinfo,
    }

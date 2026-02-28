from utils.colors import MATCH


def split_preset_name(preset):
    parts = [p.strip() for p in preset.split("-")]
    if len(parts) < 3:
        return None, None, None

    vendor = parts[0]
    material = parts[1]
    color = "-".join(parts[2:])

    if "(" in color:
        color = color.split("(")[0]

    return vendor, material, color


def find_spool_for_preset(preset, spool_cache, log):
    vendor, material, color = split_preset_name(preset)
    if not vendor:
        log.error(MATCH, f"Invalid preset format: '{preset}'")
        return None

    vendor_l = vendor.lower()
    material_l = material.lower()
    color_l = color.lower()

    exact_matches = []

    for spool in spool_cache:
        f = spool.get("filament", {})
        s_vendor = f.get("vendor", {}).get("name", "").lower()
        s_material = f.get("material", "").lower()
        s_color = f.get("name", "").lower()

        if s_vendor == vendor_l and s_material == material_l and s_color == color_l:
            exact_matches.append(spool)

    if not exact_matches:
        log.error(MATCH, f"No exact spool match for preset '{preset}'")
        return None

    selected = min(exact_matches, key=lambda s: s.get("remaining_weight", float("inf")))

    log.info(
        MATCH,
        f"Using spool ID {selected['id']} for preset '{preset}' "
        f"(remaining {selected.get('remaining_weight', 'unknown')} g)",
    )

    return selected["id"]

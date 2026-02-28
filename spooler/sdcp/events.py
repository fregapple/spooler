from ui.notify import notify
from spoolman.manager import refresh_spool_cache, update_spoolman
from spoolman.matcher import find_spool_for_preset
from utils.colors import SDCP, SPOOLMAN, DEVICE
from core.state import pending_jobs
from utils.mm_to_gram import extrusion_mm_to_grams
from core.cleanup import cleanup

import asyncio


async def handle_print_start(state, devices, config, log):
    state.active = True
    state.paused = False
    state.stopped = False
    state.waiting_for_idle = False

    log.info(SDCP, f"Print started: {state.shortname}")

    max_retries = 60

    for attempt in range(max_retries):
        if state.filename in pending_jobs:
            state.job = pending_jobs[state.filename]
            break

        if attempt % 10 == 0:
            log.info(SDCP, f"Waiting for job metadata for {state.shortname} (attempt {attempt + 1}/{max_retries})") 

        await asyncio.sleep(1)

    if not state.job:
        log.error(SDCP, f"Failed to load job metadata for {state.shortname} after {max_retries} attempts")
        return
    
    else:
        log.info(SDCP, f"Successfully loaded job metadata for {state.shortname}")

    # Device logic
    if devices and devices.airpurifier:
        if not devices.airpurifier.get_power():
            devices.airpurifier.turn_on()
        devices.airpurifier.set_fan_speed("high")
        log.info(DEVICE, "Air purifier set to high speed")


async def handle_print_pause(state, devices, config, log):
    state.paused = True
    log.info(SDCP, "Print paused")


async def handle_print_resume(state, devices, config, log):
    state.paused = False
    state.stopped = False
    log.info(SDCP, "Print resumed")


async def handle_print_stop(state, devices, config, log):
    state.stopped = True
    log.info(SDCP, "Print stopped")


async def handle_print_complete(state, devices, config, log):
    log.info(SDCP, "Print complete")

    # Notify user
    notify("Print Complete", f"{state.shortname} finished!", config.apprise_tag_custom, config, log)

    # Device logic
    if devices and devices.airpurifier:
        devices.airpurifier.set_fan_speed("mid")
        log.info(DEVICE, "Air purifier set to mid speed")

    # Spoolman logic
    job = state.job
    presets = job["filament_presets"]
    usage_list = job["filament_g_list"]


    sdcp_grams = round(extrusion_mm_to_grams(state.total_extrusions), 2)

    log.info(SDCP, f"Total extrusions: {state.total_extrusions}mm -> {sdcp_grams}g")

    if not presets or not usage_list:
        log.error(SDCP, "No filament usage data found in job metadata")
        return

    else:
        spool_cache = refresh_spool_cache(config, log)
    
    # Counter for how many presets we match to usage. If multiple presets, we will use ORCA metadata usage instead of SDCP usage for all presets, since SDCP usage is total and not per-preset.
    used = 0

    for preset, grams in zip(presets, usage_list):
        if grams <= 0:
            continue
            
        used += 1

        spool_id = find_spool_for_preset(preset, spool_cache, log)

        if not spool_id:
            log.error(SPOOLMAN, f"No spool match for {preset}")
            continue

        if used == 1:

            gram_diff = abs(float(sdcp_grams)-float(grams))

            log.info(SDCP, f"SDCP Usage: {sdcp_grams}g, ORCA Metadata Usage: {grams}g, Difference: {gram_diff}g")

            if gram_diff >= 11:
                log.warn(SDCP, f"Large discrepancy between SDCP and ORCA usage for {preset}: {gram_diff}g. Updating Spoolman, but you may have to change values manually.")
                notify("Large Discrepancy", f"Large discrepancy detected for preset {preset}: {gram_diff}g. Updating Spoolman, but you may have to change values manually.", config.apprise_tag_custom, config, log)
    
            update_spoolman(spool_id, sdcp_grams, config, log, notify_fn=notify)

        else:
            log.info(SDCP, f"Multiple presets detected. Using ORCA metadata usage of {grams}g for preset {preset}. SDCP usage was {sdcp_grams}g, but will not be used for update due to multiple presets.")
            update_spoolman(spool_id, grams, config, log, notify_fn=notify)

    # Reset state
    state.waiting_for_idle = True
    state.active = False


async def handle_idle(state, devices, config, log):
    log.info(SDCP, "Printer idle")
    log.info(SDCP, "Starting Cleanup of files")
    cleanup(state=state, config=config, log=log)

    if not config.always_running:
        log.info(SDCP, "One-shot mode: shutting down daemon")
        config.shutdown_event.set()
        return

    # Always-running mode
    if devices and devices.airpurifier:
        devices.airpurifier.sleep_mode_on()

    state.reset()
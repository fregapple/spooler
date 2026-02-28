import requests
from utils.colors import SPOOLMAN


def refresh_spool_cache(config, log):
    """
    Fetch all spools from Spoolman.
    """
    try:
        r = requests.get(f"{config.spoolman_url}/api/v1/spool")
        r.raise_for_status()
        spools = r.json()
        log.info(SPOOLMAN, f"Loaded {len(spools)} spools from Spoolman")
        return spools

    except Exception as e:
        log.error(SPOOLMAN, f"Failed to load spools: {e}")
        return []


def update_spoolman(spool_id, grams, config, log, notify_fn=None):
    """
    Deduct filament from a spool.
    """
    url = f"{config.spoolman_url}/api/v1/spool/{spool_id}/use"
    payload = {"use_weight": grams}

    try:
        r = requests.put(url, json=payload)
        r.raise_for_status()
        log.info(SPOOLMAN, f"Updated spool {spool_id}: deducted {grams}g")

        if notify_fn and config.apprise_tag_spoolman:
            notify_fn(
                f"Spool {spool_id} updated",
                f"{grams}g deducted.",
                config.apprise_tag_spoolman,
                config,
                log,
            )

    except Exception as e:
        log.error(SPOOLMAN, f"Failed to update spool {spool_id}: {e}")

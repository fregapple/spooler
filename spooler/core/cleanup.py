from pathlib import Path

from utils.colors import WATCH


def cleanup(state=None, devices=None, config=None, log=None):
    file = Path(f"{config.watch_folder}/{state.filename}")
    if file.is_file():
        file.unlink()
        log.info(WATCH, f"Deleting {state.shortname}.")

    else:
        log.error(WATCH, f"Deleting {state.shortname} Failed.. File may not exist / been removed already / or configured incorrectly.")

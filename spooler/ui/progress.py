from utils.colors import GREEN, GRAY, CYAN, RESET

BAR_LENGTH = 100
SPINNER = ["|", "/", "-", "\\"]

def render_progress(progress, spin_index):
    filled = int((progress / 100) * BAR_LENGTH)
    bar = f"{GREEN}{'█' * filled}{GRAY}{'░' * (BAR_LENGTH - filled)}{RESET}"

    spin = SPINNER[spin_index % len(SPINNER)]

    return f"\r{CYAN}[PRINTING]{RESET} {spin} {bar} {progress:3d}%"
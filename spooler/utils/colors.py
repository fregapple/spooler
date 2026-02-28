# -----------------------------
# Terminal Colors
# -----------------------------
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"
GRAY = "\033[90m"
ORANGE = "\033[38;5;208m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
DARK_GREEN = "\033[32m"
WHITE = "\033[97m"
LOG_DEBUG = "\033[38;5;178m"   
LOG_INFO = ""         
LOG_WARN = "\033[38;5;208m"    
LOG_ERROR = "\033[38;5;124m"
AQUA = "\033[38;5;44m"

# -----------------------------
# Terminal TAGS
# -----------------------------
DEVICE = f"{MAGENTA}[DEVICE]{RESET}"
SDCP = f"{BLUE}[SDCP]{RESET}"
WATCH = f"{YELLOW}[WATCH]{RESET}"
SPOOLMAN = f"{ORANGE}[SPOOLMAN]{RESET}"
APPRISE = f"{DARK_GREEN}[APPRISE]{RESET}"
RUN = f"{CYAN}[RUN]{RESET}"
ERROR = f"{RED}[ERROR]{RESET}"
MATCH = f"{GREEN}[MATCH]{RESET}"
MAIN = f"{WHITE}[MAIN]{RESET}"
CONFIG = f"{AQUA}[CONFIG]{RESET}"
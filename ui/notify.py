import requests
from utils.colors import APPRISE

def notify(title, body, tag, config, log):
    """
    Send a notification to the Apprise server.
    """

    headers = {"Content-Type": "application/json"}
    payload = {"title": title, "body": body, "tags": [tag]}

    # Determine which IP to use
    apprise_ip = config.apprise_ip or config.apprise_local_ip
    if not apprise_ip:
        log.error(APPRISE, "Apprise not configured correctly. No IP address provided.")
        return

    try:
        url = f"http://{apprise_ip}/notify/{config.apprise_config}"
        requests.post(url, json=payload, headers=headers)
        log.info(APPRISE, f"Notification sent to Apprise server: {config.apprise_config}")

    except Exception:
        log.error(APPRISE, "Apprise not reachable or misconfigured.")
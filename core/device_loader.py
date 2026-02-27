from utils.colors import DEVICE
from core.device_registry import DEVICE_REGISTRY

class DeviceContainer:
    pass

def load_devices(config, log):
    container = DeviceContainer()

    for entry in config.devices:
        dtype = entry.get("device_type", "").lower()
        model = entry.get("model")
        dev_id = entry.get("id")
        dev_key = entry.get("key")
        dev_ip = entry.get("ip")
        always_on = entry.get("always_on", False)

        if not dtype or not dev_id or not dev_key:
            log.error(DEVICE, f"Invalid device entry: {entry}")
            setattr(container, dtype or "unknown", None)
            continue

        if dtype not in DEVICE_REGISTRY:
            log.error(DEVICE, f"Unsupported device type: {dtype}")
            setattr(container, dtype, None)
            continue

        DeviceClass = DEVICE_REGISTRY[dtype]

        try:
            device = DeviceClass(
                dev_id=dev_id,
                address=dev_ip,
                local_key=dev_key,
                version=3.3,
                log=log,
                model=model,
                always_on=always_on
            )

            log.info(DEVICE, f"Loaded device: {dtype} (ID: {dev_id})")
            setattr(container, dtype, device)

        except Exception as e:
            log.error(DEVICE, f"Failed to initialize device {dtype} (ID: {dev_id}): {e}")
            setattr(container, dtype, None)

    return container

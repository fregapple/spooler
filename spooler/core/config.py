import asyncio
import json
from pathlib import Path

from utils.colors import CONFIG

# BASE_DIR = Path(__file__).parent.parent


class ConfigError(Exception):
    """Raised when the configuration file is invalid."""

    pass


class Config:
    REQUIRED_FIELDS = [
        "sdcp_ws_url",
        "watch_folder",
        "spoolman_url",
        "spoolman_local_url",
        "apprise_ip",
        "apprise_local_ip",
        "apprise_config",
        "apprise_tag_custom",
        "apprise_tag_spoolman",
        "log_level",
    ]

    OPTIONAL_FIELDS_WITH_DEFAULTS = {
        "delete_after_print": True,
        "always_running": False,
        "custom_device_always_on": False,
        "log_timestamps": True,
    }

    def __init__(self, path="../config/config.json", logger=None):
        self.logger = logger
        self.path = Path(path)
        self._data = self._load()
        self._validate_required()
        self._validate_optional_booleans()
        self._assign_attributes()
        self.shutdown_event = asyncio.Event()

    def _load(self):
        if not self.path.exists():
            if self.logger:
                self.logger.error(CONFIG, f"Config file not found: {self.path}")
                self.logger.warn(
                    CONFIG,
                    "Copy and rename the config_example.json file. Make sure to fill out all the necessary information.",
                )
            raise FileNotFoundError(f"Config file not found: {self.path}")

        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.error(CONFIG, f"Invalid JSON in config file: {e}")
            raise ConfigError(f"Invalid JSON in config file: {e}")

    def _validate_required(self):
        missing = []
        empty = []
        apprise_ip = []

        for key in self.REQUIRED_FIELDS:
            if self._data[key] != "":
                apprise_ip.append(key)
            if key not in self._data:
                missing.append(key)
            elif self._data[key] in ("", None):
                if key == "apprise_local_ip" and apprise_ip:
                    continue
                empty.append(key)

        if missing:
            if self.logger:
                self.logger.error(CONFIG, f"Missing required config fields: {', '.join(missing)}")
            raise ConfigError(f"Missing required config fields: {', '.join(missing)}")

        if empty:
            if self.logger:
                self.logger.error(
                    CONFIG,
                    f"Required config fields cannot be empty: {', '.join(empty)}",
                )
            raise ConfigError(f"Required config fields cannot be empty: {', '.join(empty)}")

    def _validate_optional_booleans(self):
        for key, default in self.OPTIONAL_FIELDS_WITH_DEFAULTS.items():
            if key not in self._data:
                self._data[key] = default
                continue

            value = self._data[key]

            if value == "":
                if self.logger:
                    self.logger.warn(
                        CONFIG,
                        f"Optional field '{key}' is empty. Using default: {default}",
                    )
                self._data[key] = default
                continue

            if not isinstance(value, bool):
                if self.logger:
                    self.logger.warn(
                        CONFIG,
                        f"Optional field '{key}' must be a boolean. Got {value!r}. Using default: {default}",
                    )
                self._data[key] = default
                continue

    def _validate_devices(self):
        devices = self._data.get("devices", [])
        if not isinstance(devices, list):
            if self.logger:
                self.logger.error(
                    CONFIG,
                    f"'devices' field must be a list. Got {type(devices).__name__}.",
                )
            raise ConfigError(f"'devices' field must be a list. Got {type(devices).__name__}.")

        for idx, device in enumerate(devices):
            if not isinstance(device, dict):
                if self.logger:
                    self.logger.error(
                        CONFIG,
                        f"Device entry at index {idx} must be an object. Got {type(device).__name__}.",
                    )
                raise ConfigError(f"Device entry at index {idx} must be an object. Got {type(device).__name__}.")

            required_device_fields = ["device_type", "id", "key"]
            for field in required_device_fields:
                if field not in device or not device[field]:
                    if self.logger:
                        self.logger.error(
                            CONFIG,
                            f"Device entry at index {idx} is missing required field '{field}' or it is empty.",
                        )
                    raise ConfigError(
                        f"Device entry at index {idx} is missing required field '{field}' or it is empty."
                    )

    def _assign_attributes(self):
        for key, value in self._data.items():
            setattr(self, key, value)

    def to_dict(self):
        return dict(self._data)

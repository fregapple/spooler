import asyncio
from pathlib import Path
from urllib.parse import urlparse

import yaml

from utils.colors import CONFIG

# BASE_DIR = Path(__file__).parent.parent


class ConfigError(Exception):
    """Raised when the configuration file is invalid."""

    pass


class Config:
    DEFAULT_CONFIG_CANDIDATES = [
        "../config/config.yaml",
        "../config/config.yml",
    ]

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

    def __init__(self, path=None, logger=None):
        self.logger = logger
        self.path = self._resolve_path(path)
        self._data = self._load()
        self._data = self._normalize_config(self._data)
        self._validate_required()
        self._validate_optional_booleans()
        self._validate_devices()
        self._assign_attributes()
        self.shutdown_event = asyncio.Event()

    def _resolve_path(self, configured_path):
        if configured_path:
            return Path(configured_path)

        for candidate in self.DEFAULT_CONFIG_CANDIDATES:
            candidate_path = Path(candidate)
            if candidate_path.exists():
                return candidate_path

        # Keep the first candidate for a clear missing-file error.
        return Path(self.DEFAULT_CONFIG_CANDIDATES[0])

    @staticmethod
    def _is_structured_schema(data):
        if not isinstance(data, dict):
            return False

        structured_keys = {
            "schema_version",
            "setup",
            "global",
            "spoolman",
            "notifications",
            "printers",
            "assignments",
        }
        return any(key in data for key in structured_keys)

    @staticmethod
    def _select_primary_printer(printers):
        if not isinstance(printers, list):
            return {}

        valid_printers = [printer for printer in printers if isinstance(printer, dict)]
        if not valid_printers:
            return {}

        for printer in valid_printers:
            if printer.get("enabled", True):
                return printer

        return valid_printers[0]

    @staticmethod
    def _normalize_apprise_host(apprise_url):
        if not apprise_url:
            return apprise_url

        if "://" not in apprise_url:
            return apprise_url.split("/", 1)[0].strip()

        parsed = urlparse(apprise_url)
        return parsed.netloc.strip() if parsed.netloc else apprise_url.strip()

    def _normalize_devices(self, devices):
        if not isinstance(devices, list):
            return devices

        normalized_devices = []
        for entry in devices:
            if not isinstance(entry, dict):
                normalized_devices.append(entry)
                continue

            normalized_entry = dict(entry)
            connection = normalized_entry.get("connection")

            if isinstance(connection, dict):
                original_id = normalized_entry.get("id")
                if original_id:
                    normalized_entry.setdefault("config_id", original_id)

                normalized_entry["id"] = connection.get("device_id", normalized_entry.get("id"))
                normalized_entry["key"] = connection.get("local_key", normalized_entry.get("key"))
                normalized_entry["ip"] = connection.get("ip", normalized_entry.get("ip"))

            normalized_devices.append(normalized_entry)

        return normalized_devices

    def _normalize_config(self, data):
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        normalized["devices"] = self._normalize_devices(normalized.get("devices", []))

        if not self._is_structured_schema(data):
            return normalized

        global_cfg = data.get("global", {}) if isinstance(data.get("global"), dict) else {}
        spoolman_cfg = data.get("spoolman", {}) if isinstance(data.get("spoolman"), dict) else {}
        notifications_cfg = data.get("notifications", {}) if isinstance(data.get("notifications"), dict) else {}
        tags_cfg = notifications_cfg.get("tags", {}) if isinstance(notifications_cfg.get("tags"), dict) else {}
        primary_printer = self._select_primary_printer(data.get("printers"))

        apprise_url = notifications_cfg.get("apprise_url")
        apprise_host = self._normalize_apprise_host(apprise_url)

        normalized["sdcp_ws_url"] = (
            primary_printer.get("sdcp_ws_url")
            or normalized.get("sdcp_ws_url")
            or ""
        )
        normalized["watch_folder"] = (
            primary_printer.get("watch_folder")
            or global_cfg.get("watch_folder")
            or normalized.get("watch_folder")
            or ""
        )
        normalized["spoolman_url"] = spoolman_cfg.get("url") or normalized.get("spoolman_url") or ""
        normalized["spoolman_local_url"] = (
            spoolman_cfg.get("fallback_url")
            or normalized.get("spoolman_local_url")
            or ""
        )
        normalized["delete_after_print"] = (
            primary_printer.get("delete_after_print")
            if "delete_after_print" in primary_printer
            else global_cfg.get("delete_after_print", normalized.get("delete_after_print", True))
        )
        normalized["always_running"] = global_cfg.get("always_running", normalized.get("always_running", False))
        normalized["custom_device_always_on"] = global_cfg.get(
            "custom_device_always_on",
            normalized.get("custom_device_always_on", False),
        )
        normalized["hide_one_time_mode_terminal"] = global_cfg.get(
            "hide_one_time_mode_terminal",
            normalized.get("hide_one_time_mode_terminal", False),
        )
        normalized["log_level"] = global_cfg.get("log_level", normalized.get("log_level", "INFO"))
        normalized["log_timestamps"] = global_cfg.get("log_timestamps", normalized.get("log_timestamps", True))

        normalized["apprise_ip"] = (
            notifications_cfg.get("apprise_ip")
            or apprise_host
            or normalized.get("apprise_ip")
            or ""
        )
        normalized["apprise_local_ip"] = (
            notifications_cfg.get("apprise_local_ip")
            if "apprise_local_ip" in notifications_cfg
            else normalized.get("apprise_local_ip")
        )
        normalized["apprise_config"] = (
            notifications_cfg.get("apprise_config")
            or normalized.get("apprise_config")
            or ""
        )
        normalized["apprise_tag_custom"] = (
            tags_cfg.get("custom")
            or notifications_cfg.get("apprise_tag_custom")
            or normalized.get("apprise_tag_custom")
            or ""
        )
        normalized["apprise_tag_spoolman"] = (
            tags_cfg.get("spoolman")
            or notifications_cfg.get("apprise_tag_spoolman")
            or normalized.get("apprise_tag_spoolman")
            or ""
        )

        return normalized

    def _load(self):
        if not self.path.exists():
            if self.logger:
                self.logger.error(CONFIG, f"Config file not found: {self.path}")
                self.logger.warn(
                        CONFIG,
                        (
                            "Copy and rename config_example.yaml. "
                            "Make sure to fill out all the necessary information."
                        ),
                    )
            raise FileNotFoundError(f"Config file not found: {self.path}")

        try:
            suffix = self.path.suffix.lower()
            if suffix not in (".yaml", ".yml"):
                raise ConfigError(
                    f"Unsupported config extension '{suffix}'. Use a YAML file (.yaml or .yml)."
                )

            with open(self.path, "r") as f:
                data = yaml.safe_load(f)

                if data is None:
                    return {}

                if not isinstance(data, dict):
                    raise ConfigError("Config file root must be an object/mapping.")

                return data
        except yaml.YAMLError as e:
            if self.logger:
                self.logger.error(CONFIG, f"Invalid config format in {self.path.name}: {e}")
            raise ConfigError(f"Invalid config format in {self.path.name}: {e}")

    def _validate_required(self):
        missing = []
        empty = []

        for key in self.REQUIRED_FIELDS:
            if key not in self._data:
                missing.append(key)
            elif self._data[key] in ("", None):
                empty.append(key)

        # Accept either apprise_ip or apprise_local_ip.
        if "apprise_ip" in empty and self._data.get("apprise_local_ip"):
            empty.remove("apprise_ip")
        if "apprise_local_ip" in empty and self._data.get("apprise_ip"):
            empty.remove("apprise_local_ip")

        if missing:
            missing_list = ", ".join(missing)
            if self.logger:
                self.logger.error(CONFIG, f"Missing required config fields: {missing_list}")
            raise ConfigError(f"Missing required config fields: {missing_list}")

        if empty:
            empty_list = ", ".join(empty)
            if self.logger:
                self.logger.error(
                    CONFIG,
                    f"Required config fields cannot be empty: {empty_list}",
                )
            raise ConfigError(f"Required config fields cannot be empty: {empty_list}")

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

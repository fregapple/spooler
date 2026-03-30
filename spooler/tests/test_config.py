"""Unit tests for config loading and schema normalization."""
from core.config import Config


def test_structured_yaml_maps_to_legacy_fields(temp_dir):
    config_path = temp_dir / "config.yaml"
    config_path.write_text(
        """
schema_version: 2

global:
  log_level: DEBUG
  log_timestamps: true
  always_running: true
  delete_after_print: true

spoolman:
  enabled: true
  url: "http://spoolman:7912"
  fallback_url: "http://localhost:7912"

notifications:
  enabled: true
  apprise_url: "http://apprise.local:8009"
  apprise_config: "apprise"
  tags:
    custom: "spooler"
    spoolman: "spoolman"

printers:
  - id: "printer-a"
    name: "Printer A"
    enabled: true
    sdcp_ws_url: "ws://printer-a:3030/websocket?command=subscribe"
    watch_folder: "/tmp/watch-a"

devices:
  - id: "airpurifier-main"
    device_type: "airpurifier"
    model: "LAP168"
    always_on: false
    connection:
      device_id: "tuya-id"
      local_key: "tuya-key"
      ip: "Auto"
""".strip()
    )

    config = Config(path=str(config_path))

    assert config.sdcp_ws_url == "ws://printer-a:3030/websocket?command=subscribe"
    assert config.watch_folder == "/tmp/watch-a"
    assert config.spoolman_url == "http://spoolman:7912"
    assert config.spoolman_local_url == "http://localhost:7912"
    assert config.apprise_ip == "apprise.local:8009"
    assert config.apprise_tag_custom == "spooler"
    assert config.devices[0]["id"] == "tuya-id"
    assert config.devices[0]["key"] == "tuya-key"
    assert config.devices[0]["config_id"] == "airpurifier-main"


def test_structured_yaml_selects_first_enabled_printer(temp_dir):
    config_path = temp_dir / "config.yaml"
    config_path.write_text(
        """
global:
  log_level: INFO

spoolman:
  url: "http://spoolman:7912"
  fallback_url: "http://localhost:7912"

notifications:
  apprise_url: "http://apprise:8009"
  apprise_config: "apprise"
  tags:
    custom: "spooler"
    spoolman: "spoolman"

printers:
  - id: "disabled-printer"
    enabled: false
    sdcp_ws_url: "ws://disabled:3030/websocket?command=subscribe"
    watch_folder: "/tmp/disabled"
  - id: "enabled-printer"
    enabled: true
    sdcp_ws_url: "ws://enabled:3030/websocket?command=subscribe"
    watch_folder: "/tmp/enabled"

devices: []
""".strip()
    )

    config = Config(path=str(config_path))

    assert config.sdcp_ws_url == "ws://enabled:3030/websocket?command=subscribe"
    assert config.watch_folder == "/tmp/enabled"

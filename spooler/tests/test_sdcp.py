"""Unit tests for SDCP message parsing."""
import pytest
from sdcp.parser import parse_message


class TestSDCPParser:
    """Tests for SDCP message parsing."""

    def test_parse_valid_status_message(self, mock_sdcp_status_message):
        """Should parse complete status message."""
        result = parse_message(mock_sdcp_status_message)
        assert result is not None
        assert result["machine_status"] == "printing"
        assert result["current_fan_speed"] == 80
        assert result["nozzle_temp"] == 220  # Rounded
        assert result["bed_temp"] == 60  # Rounded
        assert result["box_temp"] == 36  # Rounded
        assert result["print_status"] == "active"
        assert result["filename"] == "test_print.gcode"
        assert result["progress"] == 45

    def test_parse_message_without_status(self):
        """Should return None for messages without Status field."""
        message = {"Data": {"SomeField": "value"}}
        result = parse_message(message)
        assert result is None

    def test_parse_empty_message(self):
        """Should return None for empty message."""
        result = parse_message({})
        assert result is None

    def test_parse_idle_printer(self):
        """Should handle idle printer state."""
        message = {
            "Status": {
                "CurrentStatus": "idle",
                "CurrentFanSpeed": 0,
                "TempOfNozzle": 25.3,
                "TempOfHotbed": 23.1,
                "TempOfBox": 22.8,
                "PrintInfo": {
                    "Status": "idle",
                    "Filename": "",
                    "Progress": 0,
                },
            }
        }
        result = parse_message(message)
        assert result is not None
        assert result["machine_status"] == "idle"
        assert result["filename"] == ""
        assert result["progress"] == 0

    def test_parse_missing_printinfo(self):
        """Should handle missing PrintInfo gracefully."""
        message = {
            "Status": {
                "CurrentStatus": "offline",
                "CurrentFanSpeed": 0,
                "TempOfNozzle": 20.0,
                "TempOfHotbed": 20.0,
                "TempOfBox": 20.0,
                # PrintInfo is missing
            }
        }
        result = parse_message(message)
        assert result is not None
        assert result["machine_status"] == "offline"
        assert result["filename"] == ""
        assert result["progress"] == 0

    def test_temperature_rounding(self):
        """Should round temperatures to whole numbers."""
        message = {
            "Status": {
                "CurrentStatus": "heating",
                "CurrentFanSpeed": 50,
                "TempOfNozzle": 215.7,
                "TempOfHotbed": 59.4,
                "TempOfBox": 30.9,
                "PrintInfo": {},
            }
        }
        result = parse_message(message)
        assert result["nozzle_temp"] == 216  # Rounded up
        assert result["bed_temp"] == 59  # Rounded down
        assert result["box_temp"] == 31  # Rounded up

    def test_parse_includes_full_printinfo(self, mock_sdcp_status_message):
        """Should include complete PrintInfo dict in result."""
        result = parse_message(mock_sdcp_status_message)
        assert "printinfo" in result
        assert result["printinfo"]["Status"] == "active"
        assert result["printinfo"]["Filename"] == "test_print.gcode"
        assert result["printinfo"]["Progress"] == 45

    def test_parse_various_status_values(self):
        """Should handle different machine status values."""
        statuses = ["printing", "paused", "idle", "error", "offline"]
        for status in statuses:
            message = {
                "Status": {
                    "CurrentStatus": status,
                    "CurrentFanSpeed": 0,
                    "TempOfNozzle": 20.0,
                    "TempOfHotbed": 20.0,
                    "TempOfBox": 20.0,
                    "PrintInfo": {},
                }
            }
            result = parse_message(message)
            assert result is not None
            assert result["machine_status"] == status

    def test_parse_high_precision_temps(self):
        """Should handle and round high-precision temperature values."""
        message = {
            "Status": {
                "CurrentStatus": "printing",
                "CurrentFanSpeed": 100,
                "TempOfNozzle": 220.123456789,
                "TempOfHotbed": 60.987654321,
                "TempOfBox": 35.5,
                "PrintInfo": {},
            }
        }
        result = parse_message(message)
        assert isinstance(result["nozzle_temp"], int)
        assert isinstance(result["bed_temp"], int)
        assert isinstance(result["box_temp"], int)

    def test_parse_progress_edge_cases(self):
        """Should handle progress at 0 and 100."""
        for progress in [0, 50, 100]:
            message = {
                "Status": {
                    "CurrentStatus": "printing",
                    "CurrentFanSpeed": 50,
                    "TempOfNozzle": 220.0,
                    "TempOfHotbed": 60.0,
                    "TempOfBox": 35.0,
                    "PrintInfo": {"Progress": progress, "Filename": "test.gcode"},
                }
            }
            result = parse_message(message)
            assert result["progress"] == progress

    def test_parse_long_filename(self):
        """Should handle long filenames."""
        long_filename = "very_long_filename_" * 10 + ".gcode"
        message = {
            "Status": {
                "CurrentStatus": "printing",
                "CurrentFanSpeed": 50,
                "TempOfNozzle": 220.0,
                "TempOfHotbed": 60.0,
                "TempOfBox": 35.0,
                "PrintInfo": {"Filename": long_filename},
            }
        }
        result = parse_message(message)
        assert result["filename"] == long_filename

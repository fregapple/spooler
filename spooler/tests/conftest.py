"""Pytest configuration and shared fixtures."""
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory that gets cleaned up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_gcode_file(temp_dir):
    """Create a sample G-code file for testing."""
    gcode_content = """
; filament_settings_id = "Bambu Lab PLA Basic @BBL X1C" "Hatchbox - PLA - Red"
; filament used [g] = 45.23, 12.67
G28 ; home all axes
G1 X10 Y10 Z0.2 F3000
G1 E10 F1500
"""
    gcode_path = temp_dir / "test.gcode"
    gcode_path.write_text(gcode_content)
    return gcode_path


@pytest.fixture
def sample_gcode_with_purge(temp_dir):
    """Create a G-code file with purge-line usage (<1g)."""
    gcode_content = """
; filament_settings_id = "Main Filament" "Purge Tower"
; filament used [g] = 45.23, 0.67
G28
"""
    gcode_path = temp_dir / "test_purge.gcode"
    gcode_path.write_text(gcode_content)
    return gcode_path


@pytest.fixture
def mock_spools():
    """Sample spool cache data."""
    return [
        {
            "id": 1,
            "remaining_weight": 500.0,
            "filament": {
                "vendor": {"name": "Bambu Lab"},
                "material": "PLA",
                "name": "Basic",
            },
        },
        {
            "id": 2,
            "remaining_weight": 800.0,
            "filament": {
                "vendor": {"name": "Hatchbox"},
                "material": "PLA",
                "name": "Red",
            },
        },
        {
            "id": 3,
            "remaining_weight": 200.0,  # Lower weight
            "filament": {
                "vendor": {"name": "Hatchbox"},
                "material": "PLA",
                "name": "Red",
            },
        },
    ]


@pytest.fixture
def mock_sdcp_status_message():
    """Sample SDCP status message."""
    return {
        "Status": {
            "CurrentStatus": "printing",
            "CurrentFanSpeed": 80,
            "TempOfNozzle": 220.5,
            "TempOfHotbed": 60.2,
            "TempOfBox": 35.8,
            "PrintInfo": {
                "Status": "active",
                "Filename": "test_print.gcode",
                "Progress": 45,
            },
        }
    }

"""Unit tests for Spoolman matcher."""
from unittest.mock import MagicMock

import pytest
from spoolman.matcher import find_spool_for_preset, split_preset_name


class TestPresetNameSplitting:
    """Tests for splitting filament preset names into components."""

    def test_valid_preset(self):
        """Should split standard preset format."""
        vendor, material, color = split_preset_name("Bambu Lab - PLA - Blue")
        assert vendor == "Bambu Lab"
        assert material == "PLA"
        assert color == "Blue"

    def test_preset_with_multi_word_color(self):
        """Should handle color names with hyphens."""
        vendor, material, color = split_preset_name("Hatchbox - PLA - Sky Blue")
        assert vendor == "Hatchbox"
        assert material == "PLA"
        assert color == "Sky Blue"

    def test_preset_with_extra_info_in_parens(self):
        """Should strip parenthetical info from color."""
        vendor, material, color = split_preset_name("Bambu Lab - PLA - Red (Matte)")
        assert vendor == "Bambu Lab"
        assert material == "PLA"
        assert color == "Red"  # (Matte) should be stripped

    def test_preset_with_special_material(self):
        """Should handle complex material names."""
        vendor, material, color = split_preset_name("eSun - PLA+ - Black")
        assert vendor == "eSun"
        assert material == "PLA+"
        assert color == "Black"

    def test_invalid_preset_too_few_parts(self):
        """Should return None for invalid format."""
        vendor, material, color = split_preset_name("Invalid")
        assert vendor is None
        assert material is None
        assert color is None

    def test_invalid_preset_missing_parts(self):
        """Should return None when missing material or color."""
        vendor, material, color = split_preset_name("Vendor - Material")
        assert vendor is None
        assert material is None
        assert color is None

    def test_preset_with_extra_spaces(self):
        """Should strip extra whitespace."""
        vendor, material, color = split_preset_name("  Bambu Lab  -  PLA  -  Blue  ")
        assert vendor == "Bambu Lab"
        assert material == "PLA"
        assert color == "Blue"


class TestSpoolMatching:
    """Tests for finding matching spools in cache."""

    def test_exact_match_single_spool(self, mock_spools):
        """Should find exact match when one exists."""
        mock_log = MagicMock()
        result = find_spool_for_preset("Bambu Lab - PLA - Basic", mock_spools, mock_log)
        assert result is not None
        assert result == 1  # Returns spool ID (int)

    def test_exact_match_lowest_remaining(self, mock_spools):
        """Should select spool with lowest remaining weight when multiple matches."""
        mock_log = MagicMock()
        # Both spool 2 and 3 match "Hatchbox - PLA - Red", but 3 has less remaining
        result = find_spool_for_preset("Hatchbox - PLA - Red", mock_spools, mock_log)
        assert result is not None
        assert result == 3  # Should pick the one with 200g, not 800g (returns ID)

    def test_no_match_returns_none(self, mock_spools):
        """Should return None when no match found."""
        mock_log = MagicMock()
        result = find_spool_for_preset("Unknown - PETG - Green", mock_spools, mock_log)
        assert result is None
        # Should log error
        mock_log.error.assert_called()

    def test_case_insensitive_matching(self):
        """Should match regardless of case."""
        mock_log = MagicMock()
        spools = [
            {
                "id": 1,
                "remaining_weight": 500.0,
                "filament": {
                    "vendor": {"name": "bambu lab"},
                    "material": "pla",
                    "name": "basic",
                },
            }
        ]
        result = find_spool_for_preset("Bambu Lab - PLA - Basic", spools, mock_log)
        assert result is not None
        assert result == 1  # Returns spool ID (int)

    def test_invalid_preset_format(self, mock_spools):
        """Should return None and log error for invalid preset format."""
        mock_log = MagicMock()
        result = find_spool_for_preset("InvalidPreset", mock_spools, mock_log)
        assert result is None
        mock_log.error.assert_called()

    def test_partial_match_not_accepted(self):
        """Should not match if vendor, material, or color don't all match."""
        mock_log = MagicMock()
        spools = [
            {
                "id": 1,
                "remaining_weight": 500.0,
                "filament": {
                    "vendor": {"name": "Bambu Lab"},
                    "material": "PLA",
                    "name": "Blue",  # Different color
                },
            }
        ]
        result = find_spool_for_preset("Bambu Lab - PLA - Red", spools, mock_log)
        assert result is None

    def test_empty_spool_cache(self):
        """Should return None when spool cache is empty."""
        mock_log = MagicMock()
        result = find_spool_for_preset("Bambu Lab - PLA - Basic", [], mock_log)
        assert result is None

    def test_spool_with_missing_fields(self):
        """Should handle spools with missing/malformed data."""
        mock_log = MagicMock()
        spools = [
            {
                "id": 1,
                "remaining_weight": 500.0,
                "filament": {},  # Missing vendor/material/name
            }
        ]
        result = find_spool_for_preset("Bambu Lab - PLA - Basic", spools, mock_log)
        assert result is None

    def test_logs_successful_match(self, mock_spools):
        """Should log info when match is found."""
        mock_log = MagicMock()
        result = find_spool_for_preset("Bambu Lab - PLA - Basic", mock_spools, mock_log)
        assert result is not None
        # Should log info about the match
        mock_log.info.assert_called()
        # Check the log message contains relevant info
        call_args = str(mock_log.info.call_args)
        assert "spool ID 1" in call_args or "500" in call_args

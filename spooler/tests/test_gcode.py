"""Unit tests for G-code parsing and normalization."""
import pytest
from gcode.normalizer import normalize_filament_usage
from gcode.parser import parse_gcode_metadata


class TestFilamentNormalization:
    """Tests for filament usage normalization (purge-line handling)."""

    def test_no_purge_line(self):
        """Should return unchanged when no <1g usage."""
        presets = ["Filament A", "Filament B"]
        usage = [45.5, 12.3]
        result_presets, result_usage = normalize_filament_usage(presets, usage)
        assert result_presets == presets
        assert result_usage == [45.5, 12.3]

    def test_single_purge_line(self):
        """Should add <1g to largest filament."""
        presets = ["Main", "Purge"]
        usage = [45.5, 0.67]
        result_presets, result_usage = normalize_filament_usage(presets, usage)
        assert result_presets == presets
        assert result_usage[0] == pytest.approx(46.17)  # 45.5 + 0.67
        assert result_usage[1] == 0

    def test_multiple_purge_lines(self):
        """Should add all <1g amounts to largest filament."""
        presets = ["Main", "Support", "PurgeTower"]
        usage = [45.5, 0.67, 0.23]
        result_presets, result_usage = normalize_filament_usage(presets, usage)
        assert result_usage[0] == pytest.approx(46.4)  # 45.5 + 0.67 + 0.23
        assert result_usage[1] == 0
        assert result_usage[2] == 0

    def test_largest_is_purge(self):
        """Should not add to self if largest is <1g (edge case)."""
        presets = ["Small1", "Small2"]
        usage = [0.5, 0.3]
        result_presets, result_usage = normalize_filament_usage(presets, usage)
        # Largest (0.5) should get the 0.3 added
        assert result_usage[0] == pytest.approx(0.8)
        assert result_usage[1] == 0

    def test_empty_lists(self):
        """Should handle empty inputs gracefully."""
        result_presets, result_usage = normalize_filament_usage([], [])
        assert result_presets == []
        assert result_usage == []

    def test_none_inputs(self):
        """Should handle None inputs."""
        result_presets, result_usage = normalize_filament_usage(None, None)
        assert result_presets == []
        assert result_usage == []

    def test_exactly_one_gram(self):
        """Should not normalize filament with exactly 1g."""
        presets = ["Main", "Secondary"]
        usage = [45.5, 1.0]
        result_presets, result_usage = normalize_filament_usage(presets, usage)
        assert result_usage == [45.5, 1.0]  # No change


class TestGcodeParser:
    """Tests for G-code metadata extraction."""

    def test_parse_valid_gcode(self, sample_gcode_file):
        """Should extract filament presets and usage."""
        result = parse_gcode_metadata(str(sample_gcode_file))
        assert "filament_presets" in result
        assert "filament_g_list" in result
        assert "path" in result
        assert len(result["filament_presets"]) == 2
        assert result["filament_presets"][0] == "Bambu Lab PLA Basic @BBL X1C"
        assert result["filament_presets"][1] == "Hatchbox - PLA - Red"
        # Values should be normalized (small values added to largest)
        assert result["filament_g_list"][0] == pytest.approx(45.23)  # First value
        assert result["filament_g_list"][1] == pytest.approx(12.67)  # Second value

    def test_parse_nonexistent_file(self):
        """Should return empty lists for non-existent file."""
        result = parse_gcode_metadata("/nonexistent/file.gcode")
        assert result["filament_presets"] == []
        assert result["filament_g_list"] == []
        assert result["path"] == "/nonexistent/file.gcode"

    def test_parse_file_without_metadata(self, temp_dir):
        """Should return empty lists when metadata is missing."""
        gcode_path = temp_dir / "no_meta.gcode"
        gcode_path.write_text("G28\nG1 X10 Y10")
        result = parse_gcode_metadata(str(gcode_path))
        assert result["filament_presets"] == []
        assert result["filament_g_list"] == []

    def test_parse_single_filament(self, temp_dir):
        """Should handle single filament prints."""
        gcode_content = '; filament_settings_id = "Single Filament"\n; filament used [g] = 123.45\n'
        gcode_path = temp_dir / "single.gcode"
        gcode_path.write_text(gcode_content)
        result = parse_gcode_metadata(str(gcode_path))
        assert len(result["filament_presets"]) == 1
        assert len(result["filament_g_list"]) == 1
        assert result["filament_g_list"][0] == pytest.approx(123.45)

    def test_parse_with_purge_normalization(self, sample_gcode_with_purge):
        """Should normalize purge tower usage."""
        result = parse_gcode_metadata(str(sample_gcode_with_purge))
        # Main filament should have purge added (45.23 + 0.67 = 45.9)
        assert result["filament_g_list"][0] == pytest.approx(45.9)
        # Purge should be 0
        assert result["filament_g_list"][1] == 0

    def test_case_insensitive_parsing(self, temp_dir):
        """Should parse regardless of case."""
        gcode_content = '; FILAMENT_SETTINGS_ID = "TEST"\n; FILAMENT USED [G] = 50.0\n'
        gcode_path = temp_dir / "uppercase.gcode"
        gcode_path.write_text(gcode_content)
        result = parse_gcode_metadata(str(gcode_path))
        assert len(result["filament_presets"]) == 1
        assert len(result["filament_g_list"]) == 1

    def test_early_termination(self, temp_dir):
        """Should stop reading after finding both metadata fields."""
        # Create a large file with metadata at the top
        gcode_content = (
            '; filament_settings_id = "Test Filament"\n'
            '; filament used [g] = 100.0\n'
            + ('G1 X0 Y0\n' * 10000)  # Add many lines after
        )
        gcode_path = temp_dir / "large.gcode"
        gcode_path.write_text(gcode_content)
        result = parse_gcode_metadata(str(gcode_path))
        # Should still parse correctly without reading entire file
        assert len(result["filament_presets"]) == 1
        assert result["filament_g_list"][0] == pytest.approx(100.0)

"""Unit tests for utility functions."""
import pytest
from utils.mm_to_gram import extrusion_mm_to_grams


class TestExtrusionConversion:
    """Tests for filament extrusion mm to grams conversion."""

    def test_zero_extrusion(self):
        """Should return 0 for zero extrusion."""
        assert extrusion_mm_to_grams(0) == 0.0

    def test_negative_extrusion(self):
        """Should return 0 for negative extrusion."""
        assert extrusion_mm_to_grams(-100) == 0.0

    def test_standard_pla_conversion(self):
        """Test conversion with standard PLA settings (1.75mm, 1.24 g/cm³)."""
        # 1000mm of 1.75mm PLA filament
        result = extrusion_mm_to_grams(1000.0, diameter_mm=1.75, density_g_cm3=1.24)
        # Expected: π * (0.875)² * 1000 / 1000 * 1.24 ≈ 2.98g
        assert 2.9 < result < 3.1

    def test_small_extrusion(self):
        """Test small extrusion amounts (e.g., prime line)."""
        result = extrusion_mm_to_grams(10.0, diameter_mm=1.75, density_g_cm3=1.24)
        assert result > 0
        assert result < 0.1  # Should be very small

    def test_larger_diameter_filament(self):
        """Test with 2.85mm filament."""
        result_175 = extrusion_mm_to_grams(1000.0, diameter_mm=1.75, density_g_cm3=1.24)
        result_285 = extrusion_mm_to_grams(1000.0, diameter_mm=2.85, density_g_cm3=1.24)
        # 2.85mm should result in more grams for same length
        assert result_285 > result_175
        # Approximately (2.85/1.75)² times more
        assert 2.5 < result_285 / result_175 < 2.8

    def test_different_density(self):
        """Test with different material densities (PETG vs PLA)."""
        pla_result = extrusion_mm_to_grams(1000.0, diameter_mm=1.75, density_g_cm3=1.24)
        petg_result = extrusion_mm_to_grams(1000.0, diameter_mm=1.75, density_g_cm3=1.27)
        # PETG should be slightly heavier
        assert petg_result > pla_result

    def test_realistic_print_amount(self):
        """Test realistic print amounts (e.g., 50g object needs ~16500mm of filament)."""
        # For 50g of PLA filament, we need approximately 16500mm
        result = extrusion_mm_to_grams(16500.0, diameter_mm=1.75, density_g_cm3=1.24)
        assert 48 < result < 52  # Should be close to 50g

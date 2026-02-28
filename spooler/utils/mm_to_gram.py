import math


def extrusion_mm_to_grams(extrusion_mm: float, diameter_mm: float = 1.75, density_g_cm3: float = 1.24) -> float:
    """
    Convert SDCP extrusion length (mm of filament) into grams.

    extrusion_mm: length of filament exruded in millimetres
    diameter_mm: filament diameter (default 1.75 as per my profile)
    density_g_cm3: material density (default PLA at 1.24 g/cm3)
    """

    if extrusion_mm <= 0:
        return 0.0

    radius_mm = diameter_mm / 2
    cross_section_mm2 = math.pi * (radius_mm**2)

    volume_mm3 = extrusion_mm * cross_section_mm2

    # Convert mm3 to cm3 (1000 mm3 = 1 cm3)

    volume_cm3 = volume_mm3 / 1000.0

    grams = volume_cm3 * density_g_cm3

    return grams

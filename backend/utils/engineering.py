"""Engineering calculations for petroleum drilling monitoring.

These are display/analysis calculations for engineers.
They are intentionally separate from detection logic.
"""
from __future__ import annotations

PSI_TO_PA = 6894.76
GRAVITY = 9.81


def calculate_density(pressure_diff_psi: float, delta_h_m: float) -> float | None:
    """Compute mud density from differential pressure and height difference.

    Formula: ρ = ΔP / (g × Δh)
    Units:   ΔP in PSI → converted to Pa; Δh in meters → ρ in kg/m³
    """
    if delta_h_m <= 0:
        return None
    pressure_diff_pa = pressure_diff_psi * PSI_TO_PA
    density = pressure_diff_pa / (GRAVITY * delta_h_m)
    return round(density, 4)

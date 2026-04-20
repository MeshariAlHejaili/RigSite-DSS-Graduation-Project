"""Pure engineering calculations for drilling-derived metrics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PSI_TO_PA = 6894.76


@dataclass(frozen=True)
class EngineeringInputs:
    pressure_diff_psi: float
    delta_h_ft: float
    pipe_diameter_m: float
    sensor_spacing_m: float
    fluid_velocity_m_s: float
    cuttings_density_ppg: float
    cuttings_volume_fraction: float
    suspension_factor: float
    display_mud_weight: Literal["normal", "cuttings"]


@dataclass(frozen=True)
class EngineeringMetrics:
    mud_weight: float | None
    normal_mud_weight: float | None
    mud_weight_with_cuttings: float | None
    viscosity: float | None


def psi_to_pa(pressure_psi: float) -> float:
    return pressure_psi * PSI_TO_PA


def calculate_normal_mud_weight(delta_p_psi: float, delta_h_ft: float) -> float | None:
    """MW = delta_p / (0.052 * delta_h), where delta_p is psi and delta_h is ft."""
    if delta_h_ft <= 0:
        return None
    return round(delta_p_psi / (0.052 * delta_h_ft), 4)


def calculate_viscosity(
    delta_p_pa: float,
    pipe_diameter_m: float,
    sensor_spacing_m: float,
    fluid_velocity_m_s: float,
) -> float | None:
    """mu = (delta_p * D^2) / (32 * L * v), yielding Pa*s."""
    if sensor_spacing_m <= 0 or fluid_velocity_m_s == 0:
        return None
    numerator = delta_p_pa * (pipe_diameter_m ** 2)
    denominator = 32.0 * sensor_spacing_m * fluid_velocity_m_s
    return round(numerator / denominator, 4)


def calculate_mud_weight_with_cuttings(
    clean_mud_weight_ppg: float | None,
    cuttings_density_ppg: float,
    cuttings_volume_fraction: float,
    suspension_factor: float,
) -> float | None:
    """MW_mix = MW_m + alpha(dp) * phi_t * (MW_c - MW_m)."""
    if clean_mud_weight_ppg is None:
        return None
    mixed = clean_mud_weight_ppg + (
        suspension_factor * cuttings_volume_fraction * (cuttings_density_ppg - clean_mud_weight_ppg)
    )
    return round(mixed, 4)


def select_display_mud_weight(
    normal_mud_weight: float | None,
    mud_weight_with_cuttings: float | None,
    display_mud_weight: Literal["normal", "cuttings"],
) -> float | None:
    if display_mud_weight == "cuttings" and mud_weight_with_cuttings is not None:
        return mud_weight_with_cuttings
    return normal_mud_weight


def calculate_metrics(inputs: EngineeringInputs) -> EngineeringMetrics:
    """Calculate all derived engineering metrics in one pure pass."""
    normal_mud_weight = calculate_normal_mud_weight(inputs.pressure_diff_psi, inputs.delta_h_ft)
    viscosity = calculate_viscosity(
        delta_p_pa=psi_to_pa(inputs.pressure_diff_psi),
        pipe_diameter_m=inputs.pipe_diameter_m,
        sensor_spacing_m=inputs.sensor_spacing_m,
        fluid_velocity_m_s=inputs.fluid_velocity_m_s,
    )
    mud_weight_with_cuttings = calculate_mud_weight_with_cuttings(
        clean_mud_weight_ppg=normal_mud_weight,
        cuttings_density_ppg=inputs.cuttings_density_ppg,
        cuttings_volume_fraction=inputs.cuttings_volume_fraction,
        suspension_factor=inputs.suspension_factor,
    )
    mud_weight = select_display_mud_weight(
        normal_mud_weight=normal_mud_weight,
        mud_weight_with_cuttings=mud_weight_with_cuttings,
        display_mud_weight=inputs.display_mud_weight,
    )
    return EngineeringMetrics(
        mud_weight=mud_weight,
        normal_mud_weight=normal_mud_weight,
        mud_weight_with_cuttings=mud_weight_with_cuttings,
        viscosity=viscosity,
    )

"""Season OpEx model: Agrobo fleet vs a conventional fresh-market tomato baseline.

All rates are modelled assumptions (see config/economics.yaml to override);
the simulation supplies the activity quantities (robot hours, kWh, kg, inputs).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class EconAssumptions:
    labour_usd_h: float = 22.0
    electricity_usd_kwh: float = 0.16
    robot_maint_usd_h: float = 1.10          # wear parts, laser diodes, grippers
    supervision_h_per_ha_season: float = 18.0  # remote ops / field tech, Agrobo case
    amort_seasons: int = 10                  # 5-year life, 2 seasons/year
    # Fleet unit costs (BOM targets at 100-unit volume) and coverage of shared assets
    ugv_modular_usd: float = 55000.0         # chassis + 3 implements + 2 arms
    ugv_hours_per_day: float = 18.0          # day + lit night operation, 2 h charge/maintenance
    uav_usd: float = 12000.0
    uav_ha: float = 200.0
    hauler_usd: float = 30000.0
    hauler_ha: float = 8.0
    hub_usd: float = 150000.0                # grading line, packer, pre-cooler, cold room
    hub_ha: float = 40.0
    prep_ugv_usd: float = 90000.0
    prep_ha: float = 60.0
    herbicide_usd_l: float = 28.0
    n_fert_usd_kg: float = 2.4
    # Conventional baseline (UC Davis cost-study style, fresh-market tomato)
    conv_harvest_kg_per_h: float = 85.0      # hand harvest + field packing
    conv_weeding_h_ha: float = 160.0         # hand hoeing passes on top of herbicide
    conv_herbicide_l_ha: float = 5.5
    conv_n_kg_ha: float = 220.0              # uniform broadcast + fertigation
    conv_other_labour_h_ha: float = 260.0    # transplant, scouting, irrigation, sorting
    conv_machinery_usd_ha: float = 2600.0


def fleet_capex_per_ha(a: EconAssumptions, peak_ugv_hours_per_day_per_ha: float):
    """Fleet sized for the peak 7-day UGV workload (harvest peak), shared assets by coverage."""
    ugv_per_ha = peak_ugv_hours_per_day_per_ha / a.ugv_hours_per_day
    parts = dict(ugv=ugv_per_ha * a.ugv_modular_usd, uav=a.uav_usd / a.uav_ha, hauler=a.hauler_usd / a.hauler_ha,
                 hub=a.hub_usd / a.hub_ha, prep=a.prep_ugv_usd / a.prep_ha)
    return dict(ugv_per_ha=round(ugv_per_ha, 3), parts={k: round(v) for k, v in parts.items()},
                total_usd_ha=round(sum(parts.values())))


def agrobo_opex(a: EconAssumptions, area_ha, robot_hours, energy_kwh, n_applied_kg, herbicide_l, harvested_kg,
                fleet_capex_usd_ha=38000.0):
    lines = dict(
        energy=energy_kwh * a.electricity_usd_kwh,
        maintenance=robot_hours * a.robot_maint_usd_h,
        supervision=a.supervision_h_per_ha_season * area_ha * a.labour_usd_h,
        fleet_amortisation=fleet_capex_usd_ha * area_ha / a.amort_seasons,
        nitrogen=n_applied_kg * a.n_fert_usd_kg,
        herbicide=herbicide_l * a.herbicide_usd_l,
    )
    total = sum(lines.values())
    return dict(lines={k: round(v, 2) for k, v in lines.items()}, total_usd=round(total, 2),
                usd_per_kg=round(total / max(harvested_kg, 1e-6), 4))


def conventional_opex(a: EconAssumptions, area_ha, harvested_kg):
    labour_h = harvested_kg / a.conv_harvest_kg_per_h + (a.conv_weeding_h_ha + a.conv_other_labour_h_ha) * area_ha
    lines = dict(
        labour=labour_h * a.labour_usd_h,
        machinery=a.conv_machinery_usd_ha * area_ha,
        nitrogen=a.conv_n_kg_ha * area_ha * a.n_fert_usd_kg,
        herbicide=a.conv_herbicide_l_ha * area_ha * a.herbicide_usd_l,
    )
    total = sum(lines.values())
    return dict(lines={k: round(v, 2) for k, v in lines.items()}, total_usd=round(total, 2), labour_h=round(labour_h, 1),
                usd_per_kg=round(total / max(harvested_kg, 1e-6), 4))


def assumptions_dict(a: EconAssumptions):
    return asdict(a)

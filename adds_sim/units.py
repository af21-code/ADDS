"""Shared unit-conversion helpers for simulator display values."""

from __future__ import annotations


GASOLINE_DENSITY_KG_PER_LITER = 0.745


def fuel_kg_to_ml(fuel_mass_kg: float) -> float:
    """Convert fuel mass to approximate gasoline volume for dashboards and reports."""

    return fuel_mass_kg / GASOLINE_DENSITY_KG_PER_LITER * 1_000.0

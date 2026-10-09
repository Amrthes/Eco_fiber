"""Canonical observation schema and property-specific unit definitions."""

from __future__ import annotations

from typing import Final

CANONICAL_COLUMNS: Final[tuple[str, ...]] = (
    "record_id",
    "source_type",
    "source_id",
    "publication_title",
    "doi_or_url",
    "fibre_type",
    "matrix_type",
    "treatment_method",
    "naoh_concentration_pct",
    "treatment_time_h",
    "fibre_loading_wt_pct",
    "fibre_length_mm",
    "fibre_form",
    "fabrication_method",
    "test_type",
    "test_standard",
    "measured_value",
    "measured_unit",
    "specimen_id",
    "batch_id",
    "notes",
)

REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "record_id",
    "source_type",
    "source_id",
    "test_type",
    "measured_value",
    "measured_unit",
)

TEXT_COLUMNS: Final[tuple[str, ...]] = tuple(
    column
    for column in CANONICAL_COLUMNS
    if column
    not in {
        "naoh_concentration_pct",
        "treatment_time_h",
        "fibre_loading_wt_pct",
        "fibre_length_mm",
        "measured_value",
    }
)

NUMERIC_COLUMNS: Final[tuple[str, ...]] = (
    "naoh_concentration_pct",
    "treatment_time_h",
    "fibre_loading_wt_pct",
    "fibre_length_mm",
    "measured_value",
)

OPTIONAL_NUMERIC_CONSTRAINTS: Final[dict[str, tuple[float, float | None]]] = {
    "naoh_concentration_pct": (0.0, 100.0),
    "treatment_time_h": (0.0, None),
    "fibre_loading_wt_pct": (0.0, 100.0),
    "fibre_length_mm": (0.0, None),
}

TEST_TYPES: Final[frozenset[str]] = frozenset(
    {
        "tensile_strength",
        "flexural_strength",
        "impact_resistance",
        "water_absorption",
    }
)

_UNIT_ALIASES: Final[dict[str, str]] = {
    "mpa": "MPa",
    "kj/m2": "kJ/m^2",
    "kj/m^2": "kJ/m^2",
    "kj/m²": "kJ/m^2",
    "j/m": "J/m",
    "%": "%",
}

SUPPORTED_UNITS: Final[dict[str, frozenset[str]]] = {
    "tensile_strength": frozenset({"MPa"}),
    "flexural_strength": frozenset({"MPa"}),
    "impact_resistance": frozenset({"kJ/m^2", "J/m"}),
    "water_absorption": frozenset({"%"}),
}


def canonical_unit(value: str) -> str | None:
    """Return the canonical spelling for a recognized unit, or ``None``."""
    return _UNIT_ALIASES.get(value.strip().casefold())

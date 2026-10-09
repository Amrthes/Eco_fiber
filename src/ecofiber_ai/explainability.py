"""Explainability and sensitivity analysis for composite property prediction."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ecofiber_ai.inference import PredictionInput, predict_property


@dataclass
class FeatureImportanceItem:
    """Importance score and scientific interpretation for one predictor feature."""

    feature: str
    relative_importance: float
    effect_direction: str
    scientific_mechanism: str


@dataclass
class ExplainabilityReport:
    """Structured report on feature importance and mechanistic attribution."""

    target: str
    is_available: bool
    status: str
    source: str
    importances: list[FeatureImportanceItem] = field(default_factory=list)
    disclaimer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SensitivitySweepResult:
    """1D sensitivity curve for a single parameter sweep."""

    parameter_name: str
    parameter_values: list[float]
    predicted_values: list[float]
    target: str
    target_unit: str
    is_available: bool = True
    is_demo_benchmark: bool = False
    disclaimer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_feature_importances(
    target: str,
    *,
    allow_demo_benchmark: bool = False,
) -> ExplainabilityReport:
    """Compute relative feature importance based on verified models or illustrative prior hypotheses.

    If allow_demo_benchmark=False and no verified trained model exists, returns status='unavailable'.
    If allow_demo_benchmark=True, returns domain-mechanics prior hypotheses from literature,
    explicitly tagged with source='illustrative_prior_hypothesis'.
    """
    if not allow_demo_benchmark:
        return ExplainabilityReport(
            target=target,
            is_available=False,
            status="unavailable",
            source="none",
            importances=[],
            disclaimer="Empirical feature importances are unavailable because no verified model is trained on real data.",
        )

    # Demo mode: Literature-derived prior mechanistic hypotheses (clearly tagged)
    if target in {"tensile_strength", "flexural_strength"}:
        items = [
            FeatureImportanceItem(
                feature="fibre_loading_wt_pct",
                relative_importance=0.42,
                effect_direction="Parabolic (peaks around 25-35 wt%)",
                scientific_mechanism="Provides primary load-bearing capacity; excessive loading (>40%) causes fiber agglomeration, dry spots, and stress concentrations.",
            ),
            FeatureImportanceItem(
                feature="naoh_concentration_pct",
                relative_importance=0.28,
                effect_direction="Optimal peak around 3-5% NaOH",
                scientific_mechanism="Alkalization removes amorphous hemicellulose and lignin, increasing fiber roughness and matrix adhesion. Higher concentrations (>8%) induce cellulose degradation and micro-pitting.",
            ),
            FeatureImportanceItem(
                feature="treatment_time_h",
                relative_importance=0.18,
                effect_direction="Positive up to 2-6 h, plateau thereafter",
                scientific_mechanism="Sufficient soaking ensures complete surface dewaxing without excessive fiber swelling or structural weakening.",
            ),
            FeatureImportanceItem(
                feature="fibre_length_mm",
                relative_importance=0.12,
                effect_direction="Positive up to critical aspect ratio (~10-15 mm)",
                scientific_mechanism="Longer fibers allow effective shear stress transfer along the interface up to the critical fiber length.",
            ),
        ]
    elif target == "impact_resistance":
        items = [
            FeatureImportanceItem(
                feature="fibre_loading_wt_pct",
                relative_importance=0.50,
                effect_direction="Monotonically increasing / leveling off",
                scientific_mechanism="Fibre pull-out and debonding dissipate impact energy, increasing composite toughness and shock resistance.",
            ),
            FeatureImportanceItem(
                feature="naoh_concentration_pct",
                relative_importance=0.25,
                effect_direction="Modest peak around 3-5%",
                scientific_mechanism="Optimizes fiber-matrix interfacial shear strength without embrittling the cellulosic core.",
            ),
            FeatureImportanceItem(
                feature="fibre_length_mm",
                relative_importance=0.15,
                effect_direction="Positive",
                scientific_mechanism="Longer fibers require more energy to pull out completely from the cracked matrix.",
            ),
            FeatureImportanceItem(
                feature="treatment_time_h",
                relative_importance=0.10,
                effect_direction="Moderate influence",
                scientific_mechanism="Moderate surface clean-up assists wet-out during high strain-rate impact loading.",
            ),
        ]
    else:  # water_absorption
        items = [
            FeatureImportanceItem(
                feature="fibre_loading_wt_pct",
                relative_importance=0.58,
                effect_direction="Strongly positive (increasing)",
                scientific_mechanism="Natural plant fibres are hydrophilic (free hydroxyl -OH groups); adding more fibre increases composite water intake and swelling.",
            ),
            FeatureImportanceItem(
                feature="naoh_concentration_pct",
                relative_importance=0.27,
                effect_direction="Negative (reduces absorption)",
                scientific_mechanism="Alkali treatment dissolves hydrophilic hemicellulose and pectin, reducing moisture uptake and swelling rate.",
            ),
            FeatureImportanceItem(
                feature="treatment_time_h",
                relative_importance=0.10,
                effect_direction="Negative (mild reduction)",
                scientific_mechanism="Longer soaking ensures higher removal of water-absorbing non-cellulosic constituents.",
            ),
            FeatureImportanceItem(
                feature="fibre_length_mm",
                relative_importance=0.05,
                effect_direction="Minor effect",
                scientific_mechanism="Fiber end capillarity contributes slightly to water entry path kinetics.",
            ),
        ]

    return ExplainabilityReport(
        target=target,
        is_available=True,
        status="demonstration_prior",
        source="illustrative_prior_hypothesis",
        importances=items,
        disclaimer="DEMONSTRATION ONLY: These relative importance scores represent domain-mechanics literature hypotheses for UI walkthrough. They are NOT empirically learned weights from a trained dataset.",
    )


def sweep_parameter(
    target: str,
    parameter: str,
    min_val: float,
    max_val: float,
    steps: int = 25,
    base_input: PredictionInput | None = None,
    allow_demo_benchmark: bool = False,
) -> SensitivitySweepResult:
    """Generate 1D parameter sensitivity curve across a specified range."""
    unit = "MPa" if "strength" in target else "%" if target == "water_absorption" else "kJ/m^2"

    if base_input is None:
        base_input = PredictionInput(
            target=target,
            fibre_loading_wt_pct=30.0,
            naoh_concentration_pct=4.0,
            treatment_time_h=4.0,
            fibre_length_mm=10.0,
        )

    if not allow_demo_benchmark:
        # Check if real prediction is possible
        probe_res = predict_property(base_input, allow_demo_benchmark=False)
        if not probe_res.is_ready:
            return SensitivitySweepResult(
                parameter_name=parameter,
                parameter_values=[],
                predicted_values=[],
                target=target,
                target_unit=unit,
                is_available=False,
                disclaimer="Sensitivity sweep unavailable because no verified model is trained for this target.",
            )

    values = list(np.linspace(min_val, max_val, steps))
    preds: list[float] = []

    for val in values:
        inp = PredictionInput(
            target=target,
            fibre_loading_wt_pct=float(val) if parameter == "fibre_loading_wt_pct" else base_input.fibre_loading_wt_pct,
            naoh_concentration_pct=float(val) if parameter == "naoh_concentration_pct" else base_input.naoh_concentration_pct,
            treatment_time_h=float(val) if parameter == "treatment_time_h" else base_input.treatment_time_h,
            fibre_length_mm=float(val) if parameter == "fibre_length_mm" else base_input.fibre_length_mm,
            fibre_type=base_input.fibre_type,
            matrix_type=base_input.matrix_type,
            treatment_method=base_input.treatment_method,
            fibre_form=base_input.fibre_form,
            fabrication_method=base_input.fabrication_method,
        )
        res = predict_property(inp, allow_demo_benchmark=allow_demo_benchmark)
        preds.append(res.predicted_value if res.predicted_value is not None else 0.0)
        if res.predicted_unit:
            unit = res.predicted_unit

    return SensitivitySweepResult(
        parameter_name=parameter,
        parameter_values=[round(v, 2) for v in values],
        predicted_values=preds,
        target=target,
        target_unit=unit,
        is_available=True,
        is_demo_benchmark=allow_demo_benchmark,
        disclaimer=(
            "DEMO SIMULATION: Sensitivity curve is generated using domain-mechanics reference formulas for demonstration."
            if allow_demo_benchmark
            else "Evaluated using verified trained model."
        ),
    )

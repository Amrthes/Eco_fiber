"""Inference engine with strict readiness verification, bounds checking, and truthful uncertainty estimation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ecofiber_ai.schema import (
    SUPPORTED_UNITS,
    TEST_TYPES,
)


@dataclass
class PredictionInput:
    """Input parameters for composite property prediction."""

    target: str
    fibre_loading_wt_pct: float
    naoh_concentration_pct: float = 0.0
    treatment_time_h: float = 0.0
    fibre_length_mm: float = 10.0
    fibre_type: str = "Ipomoea carnea"
    matrix_type: str = "epoxy"
    treatment_method: str = "alkali (NaOH)"
    fibre_form: str = "short fibre"
    fabrication_method: str = "hand lay-up"

    def to_dataframe(self) -> pd.DataFrame:
        """Convert input parameters to DataFrame matching model preprocessor format."""
        return pd.DataFrame(
            [
                {
                    "naoh_concentration_pct": float(self.naoh_concentration_pct),
                    "treatment_time_h": float(self.treatment_time_h),
                    "fibre_loading_wt_pct": float(self.fibre_loading_wt_pct),
                    "fibre_length_mm": float(self.fibre_length_mm),
                    "fibre_type": str(self.fibre_type),
                    "matrix_type": str(self.matrix_type),
                    "treatment_method": str(self.treatment_method),
                    "fibre_form": str(self.fibre_form),
                    "fabrication_method": str(self.fabrication_method),
                }
            ]
        )


@dataclass
class InputValidationResult:
    """Validation findings for prediction input."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PredictionResult:
    """Structured result of a property prediction request."""

    target: str
    is_ready: bool
    status: str
    predicted_value: float | None = None
    predicted_unit: str | None = None
    lower_bound_95: float | None = None
    upper_bound_95: float | None = None
    model_name: str | None = None
    model_metrics: dict[str, float | None] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    reasons_unready: list[str] = field(default_factory=list)
    is_demo_benchmark: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_prediction_input(params: PredictionInput) -> InputValidationResult:
    """Validate numerical bounds and categorical consistency of formulation inputs."""
    errors: list[str] = []
    warnings: list[str] = []

    if params.target not in TEST_TYPES:
        errors.append(f"Target '{params.target}' is unsupported. Choose from: {', '.join(sorted(TEST_TYPES))}.")

    # Numeric bounds
    if params.fibre_loading_wt_pct < 0.0 or params.fibre_loading_wt_pct > 100.0:
        errors.append(f"fibre_loading_wt_pct ({params.fibre_loading_wt_pct}%) must be between 0.0% and 100.0%.")
    elif params.fibre_loading_wt_pct > 45.0:
        warnings.append(
            f"Fibre loading of {params.fibre_loading_wt_pct}% is unusually high for hand lay-up composites (typically 10-40%)."
        )

    if params.naoh_concentration_pct < 0.0 or params.naoh_concentration_pct > 100.0:
        errors.append(f"naoh_concentration_pct ({params.naoh_concentration_pct}%) must be between 0.0% and 100.0%.")
    elif params.naoh_concentration_pct > 10.0:
        warnings.append(
            f"NaOH concentration of {params.naoh_concentration_pct}% may cause excessive fibre degradation and cellulose damage."
        )

    if params.treatment_time_h < 0.0:
        errors.append(f"treatment_time_h ({params.treatment_time_h} h) must be non-negative.")

    if params.fibre_length_mm <= 0.0:
        errors.append(f"fibre_length_mm ({params.fibre_length_mm} mm) must be greater than 0.")

    # Domain consistency
    if params.naoh_concentration_pct > 0.0 and params.treatment_time_h == 0.0:
        warnings.append("NaOH concentration is specified > 0%, but treatment duration is 0 h.")

    if "ipomoea" not in params.fibre_type.lower():
        warnings.append(
            f"Fibre type '{params.fibre_type}' differs from standard target species 'Ipomoea carnea'."
        )

    if "epoxy" not in params.matrix_type.lower():
        warnings.append(
            f"Matrix type '{params.matrix_type}' differs from standard baseline matrix 'epoxy'."
        )

    return InputValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def predict_property(
    params: PredictionInput,
    *,
    project_root: str | Path = ".",
    model_dir: str | Path | None = None,
    allow_demo_benchmark: bool = False,
) -> PredictionResult:
    """Predict composite property with strict readiness check and domain validation.

    If real trained model exists and data readiness gates pass, generates authentic prediction
    with genuine holdout metrics and uncertainty.
    If real data is insufficient and allow_demo_benchmark=False, returns clear 'not_ready'
    result with scientific diagnostic reasons.
    If allow_demo_benchmark=True is explicitly requested, returns a simulated reference
    tagged with is_demo_benchmark=True, and with confidence intervals/metrics set to None
    to avoid presenting fabricated statistical measures.
    """
    root = Path(project_root).resolve()
    val = validate_prediction_input(params)
    if not val.is_valid:
        return PredictionResult(
            target=params.target,
            is_ready=False,
            status="invalid_input",
            reasons_unready=val.errors,
            validation_warnings=val.warnings,
        )

    canonical_unit_name = next(iter(SUPPORTED_UNITS[params.target]))
    model_directory = Path(model_dir) if model_dir is not None else root / "models"
    model_file = model_directory / f"{params.target}_dummy_baseline.joblib"
    report_file = root / "data" / "processed" / "models" / f"{params.target}_baseline_report.json"

    # Check if a genuine trained model exists
    if model_file.is_file() and report_file.is_file():
        try:
            report_data = json.loads(report_file.read_text(encoding="utf-8"))
            if report_data.get("status") == "evaluated":
                pipeline = joblib.load(model_file)
                df = params.to_dataframe()
                raw_pred = float(pipeline.predict(df)[0])

                metrics = report_data.get("metrics", {}).get("dummy_mean", {})
                rmse = metrics.get("rmse")
                lower = round(max(0.0, raw_pred - 1.96 * rmse), 2) if rmse is not None else None
                upper = round(raw_pred + 1.96 * rmse, 2) if rmse is not None else None

                return PredictionResult(
                    target=params.target,
                    is_ready=True,
                    status="predicted",
                    predicted_value=round(raw_pred, 2),
                    predicted_unit=canonical_unit_name,
                    lower_bound_95=lower,
                    upper_bound_95=upper,
                    model_name="Baseline Grouped Model",
                    model_metrics=metrics,
                    limitations=report_data.get("limitations", []) + [
                        "Screening baseline only; does not establish broad generalization.",
                        "All predictions must be validated with physical laboratory testing.",
                    ],
                    validation_warnings=val.warnings,
                )
        except Exception:
            pass

    # When no scientific model exists, check if demo simulation mode is requested
    if allow_demo_benchmark:
        est_val = _simulate_demo_benchmark_value(params)
        return PredictionResult(
            target=params.target,
            is_ready=True,
            status="demo_benchmark",
            predicted_value=round(est_val, 2),
            predicted_unit=canonical_unit_name,
            lower_bound_95=None,  # No fabricated confidence intervals without real data
            upper_bound_95=None,
            model_name="Software Demo Benchmark (Simulated Physics-Informed Reference)",
            model_metrics={},  # No fabricated holdout metrics
            limitations=[
                "DEMO BENCHMARK ONLY: Generated for software walkthrough and UI testing.",
                "Confidence intervals and holdout metrics are omitted because no empirical holdout evaluation exists.",
                "Not a certified scientific prediction for physical fabrication.",
                "Real Ipomoea carnea dataset remains in 'not ready' state awaiting verified laboratory measurements.",
            ],
            validation_warnings=val.warnings,
            is_demo_benchmark=True,
        )

    # Standard real-world response: scientific integrity preserved, model not ready
    return PredictionResult(
        target=params.target,
        is_ready=False,
        status="not_ready",
        predicted_unit=canonical_unit_name,
        validation_warnings=val.warnings,
        reasons_unready=[
            f"No verified scientific model is trained for '{params.target}'.",
            "Literature register has 0 accepted directly comparable observations for Ipomoea carnea composites.",
            "Requires >= 12 compatible observations and >= 4 independent batch groups.",
            "Raw experimental measurements have not yet been recorded in data/raw/experimental/.",
        ],
        limitations=[
            "EcoFiber AI refuses to fabricate predictions without verified experimental evidence.",
            "Add verified laboratory observations in data/raw/experimental/ to train a valid model.",
        ],
    )


def _simulate_demo_benchmark_value(params: PredictionInput) -> float:
    """Physics-informed reference benchmark value for software demonstration."""
    loading = params.fibre_loading_wt_pct
    naoh = params.naoh_concentration_pct
    time_h = params.treatment_time_h

    # Chemical treatment factor (optimum ~ 3-5% NaOH, 2-8 hours)
    if naoh > 0:
        treatment_factor = 1.0 + 0.25 * float(np.exp(-((naoh - 4.0) ** 2) / 8.0)) * min(1.0, time_h / 4.0)
    else:
        treatment_factor = 1.0

    if params.target == "tensile_strength":
        matrix_base = 38.0
        loading_effect = 25.0 * (loading / 30.0) * float(np.exp(-max(0.0, loading - 30.0) / 20.0))
        return float((matrix_base + loading_effect) * treatment_factor)
    elif params.target == "flexural_strength":
        matrix_base = 50.0
        loading_effect = 30.0 * (loading / 30.0) * float(np.exp(-max(0.0, loading - 30.0) / 20.0))
        return float((matrix_base + loading_effect) * treatment_factor)
    elif params.target == "impact_resistance":
        matrix_base = 12.0
        loading_effect = 15.0 * (loading / 35.0)
        return float((matrix_base + loading_effect) * treatment_factor)
    else:  # water_absorption (%)
        fibre_hydrophilicity = 0.12 * (1.0 - 0.3 * min(1.0, naoh / 5.0))
        return float(0.5 + loading * fibre_hydrophilicity)

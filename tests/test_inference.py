"""Tests for inference engine, input validation, and readiness gates."""

from pathlib import Path

import pytest

from ecofiber_ai.inference import (
    PredictionInput,
    predict_property,
    validate_prediction_input,
)

PROJECT = Path(__file__).parents[1]


def test_prediction_input_validation_catches_out_of_range():
    invalid_input = PredictionInput(
        target="tensile_strength",
        fibre_loading_wt_pct=120.0,  # Invalid: > 100%
        naoh_concentration_pct=-2.0,  # Invalid: < 0%
        treatment_time_h=-5.0,  # Invalid: < 0
        fibre_length_mm=0.0,  # Invalid: <= 0
    )
    result = validate_prediction_input(invalid_input)
    assert not result.is_valid
    assert len(result.errors) == 4


def test_prediction_input_validation_flags_warnings():
    valid_with_warnings = PredictionInput(
        target="tensile_strength",
        fibre_loading_wt_pct=55.0,  # High loading warning (> 45%)
        naoh_concentration_pct=12.0,  # High chemical warning (> 10%)
        treatment_time_h=2.0,
        fibre_length_mm=10.0,
        fibre_type="Kenaf",  # Species difference warning
    )
    result = validate_prediction_input(valid_with_warnings)
    assert result.is_valid
    assert len(result.warnings) >= 2


def test_predict_property_refuses_without_ready_model_in_strict_mode():
    inp = PredictionInput(
        target="tensile_strength",
        fibre_loading_wt_pct=30.0,
        naoh_concentration_pct=4.0,
        treatment_time_h=4.0,
        fibre_length_mm=10.0,
    )
    res = predict_property(inp, project_root=PROJECT, allow_demo_benchmark=False)

    assert not res.is_ready
    assert res.status == "not_ready"
    assert res.predicted_value is None
    assert len(res.reasons_unready) > 0
    assert "No verified scientific model" in res.reasons_unready[0]


def test_predict_property_demo_mode_returns_bounded_predictions_without_fake_cis():
    for target in ("tensile_strength", "flexural_strength", "impact_resistance", "water_absorption"):
        inp = PredictionInput(
            target=target,
            fibre_loading_wt_pct=25.0,
            naoh_concentration_pct=4.0,
            treatment_time_h=4.0,
            fibre_length_mm=10.0,
        )
        res = predict_property(inp, project_root=PROJECT, allow_demo_benchmark=True)

        assert res.is_ready
        assert res.is_demo_benchmark
        assert res.predicted_value is not None
        assert res.predicted_value > 0.0
        # When simulated without an empirical holdout, confidence intervals and metrics are omitted
        assert res.lower_bound_95 is None
        assert res.upper_bound_95 is None
        assert res.model_metrics == {}
        assert len(res.limitations) > 0

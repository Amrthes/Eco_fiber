"""Tests for explainability and parameter sensitivity analysis."""

import pytest

from ecofiber_ai.explainability import compute_feature_importances, sweep_parameter


def test_feature_importances_strict_and_demo():
    for target in ("tensile_strength", "flexural_strength", "impact_resistance", "water_absorption"):
        # Strict mode: should be unavailable when no trained model exists
        strict_report = compute_feature_importances(target, allow_demo_benchmark=False)
        assert not strict_report.is_available
        assert strict_report.status == "unavailable"
        assert len(strict_report.importances) == 0

        # Demo mode: returns domain mechanics hypotheses clearly labeled
        demo_report = compute_feature_importances(target, allow_demo_benchmark=True)
        assert demo_report.is_available
        assert demo_report.status == "demonstration_prior"
        assert demo_report.source == "illustrative_prior_hypothesis"
        assert len(demo_report.importances) == 4
        total_imp = sum(item.relative_importance for item in demo_report.importances)
        assert pytest.approx(total_imp, 0.05) == 1.0

        for item in demo_report.importances:
            assert item.feature in {"fibre_loading_wt_pct", "naoh_concentration_pct", "treatment_time_h", "fibre_length_mm"}
            assert len(item.scientific_mechanism) > 10


def test_sweep_parameter_strict_and_demo():
    # Strict mode: returns unavailable when target model is not ready
    strict_res = sweep_parameter(
        target="tensile_strength",
        parameter="fibre_loading_wt_pct",
        min_val=0.0,
        max_val=40.0,
        steps=10,
        allow_demo_benchmark=False,
    )
    assert not strict_res.is_available
    assert len(strict_res.predicted_values) == 0

    # Demo mode: returns sensitivity curve
    demo_res = sweep_parameter(
        target="tensile_strength",
        parameter="fibre_loading_wt_pct",
        min_val=0.0,
        max_val=40.0,
        steps=10,
        allow_demo_benchmark=True,
    )
    assert demo_res.is_available
    assert demo_res.is_demo_benchmark
    assert len(demo_res.parameter_values) == 10
    assert len(demo_res.predicted_values) == 10
    assert demo_res.target == "tensile_strength"
    assert demo_res.target_unit == "MPa"
    assert len(demo_res.disclaimer) > 20

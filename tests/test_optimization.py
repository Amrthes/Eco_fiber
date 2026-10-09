"""Tests for constrained multi-objective formulation optimizer."""

import pytest

from ecofiber_ai.optimization import optimize_formulation


def test_optimize_formulation_returns_pareto_candidates():
    result = optimize_formulation(
        weight_tensile=0.4,
        weight_flexural=0.3,
        weight_impact=0.1,
        weight_water_reduction=0.2,
        max_water_absorption_pct=4.5,
        min_fibre_loading_pct=15.0,
        max_fibre_loading_pct=35.0,
        allow_demo_benchmark=True,
    )

    assert result.candidates_evaluated > 0
    assert len(result.top_candidates) > 0
    assert len(result.pareto_front) > 0
    assert len(result.disclaimer) > 20

    # Verify constraints are satisfied on top candidate
    top = result.top_candidates[0]
    assert 15.0 <= top.fibre_loading_wt_pct <= 35.0
    assert top.predicted_water_absorption_pct <= 4.5
    assert top.predicted_tensile_strength_mpa > 0
    assert top.predicted_flexural_strength_mpa > 0
    assert top.predicted_impact_resistance_kj_m2 > 0


def test_optimize_formulation_respects_tight_water_constraint():
    tight_result = optimize_formulation(
        max_water_absorption_pct=2.0,  # Very tight water absorption constraint
        min_fibre_loading_pct=10.0,
        max_fibre_loading_pct=30.0,
        allow_demo_benchmark=True,
    )

    for c in tight_result.top_candidates:
        assert c.predicted_water_absorption_pct <= 2.0


def test_optimize_formulation_strict_mode_unavailable():
    strict_result = optimize_formulation(
        allow_demo_benchmark=False,
    )
    assert not strict_result.is_ready
    assert strict_result.status == "unavailable"
    assert strict_result.candidates_evaluated == 0
    assert len(strict_result.top_candidates) == 0
    assert len(strict_result.pareto_front) == 0


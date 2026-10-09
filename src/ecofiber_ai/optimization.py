"""Constrained multi-objective formulation optimization for sustainable bio-composites."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from ecofiber_ai.inference import PredictionInput, predict_property


@dataclass
class OptimizationCandidate:
    """A single evaluated composite formulation candidate."""

    fibre_loading_wt_pct: float
    naoh_concentration_pct: float
    treatment_time_h: float
    fibre_length_mm: float
    predicted_tensile_strength_mpa: float
    predicted_flexural_strength_mpa: float
    predicted_impact_resistance_kj_m2: float
    predicted_water_absorption_pct: float
    overall_utility_score: float
    is_pareto_optimal: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationResult:
    """Outcome of formulation optimization search."""

    is_ready: bool
    status: str
    candidates_evaluated: int
    top_candidates: list[OptimizationCandidate]
    pareto_front: list[OptimizationCandidate]
    objective_weights: dict[str, float]
    constraints: dict[str, float]
    disclaimer: str
    is_demo_benchmark: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def optimize_formulation(
    *,
    weight_tensile: float = 0.4,
    weight_flexural: float = 0.3,
    weight_impact: float = 0.1,
    weight_water_reduction: float = 0.2,
    max_water_absorption_pct: float = 4.5,
    min_fibre_loading_pct: float = 15.0,
    max_fibre_loading_pct: float = 35.0,
    min_naoh_pct: float = 0.0,
    max_naoh_pct: float = 8.0,
    allow_demo_benchmark: bool = False,
) -> OptimizationResult:
    """Search for optimal composite formulations balancing mechanical strength and water resistance.

    If allow_demo_benchmark=False and real predictive models are not ready, returns an unavailable
    status without presenting fabricated optimums.
    If allow_demo_benchmark=True, performs a demonstration sweep explicitly tagged as simulated.
    """
    weights = {
        "weight_tensile": weight_tensile,
        "weight_flexural": weight_flexural,
        "weight_impact": weight_impact,
        "weight_water_reduction": weight_water_reduction,
    }
    constraints = {
        "max_water_absorption_pct": max_water_absorption_pct,
        "min_fibre_loading_pct": min_fibre_loading_pct,
        "max_fibre_loading_pct": max_fibre_loading_pct,
        "min_naoh_pct": min_naoh_pct,
        "max_naoh_pct": max_naoh_pct,
    }

    if not allow_demo_benchmark:
        # Check if real models exist for targets
        probe = PredictionInput(target="tensile_strength", fibre_loading_wt_pct=25.0)
        res = predict_property(probe, allow_demo_benchmark=False)
        if not res.is_ready:
            return OptimizationResult(
                is_ready=False,
                status="unavailable",
                candidates_evaluated=0,
                top_candidates=[],
                pareto_front=[],
                objective_weights=weights,
                constraints=constraints,
                disclaimer="Optimization is unavailable because verified predictive models have not been trained for the required targets. Real data readiness gates must be satisfied first.",
                is_demo_benchmark=False,
            )

    loadings = np.linspace(min_fibre_loading_pct, max_fibre_loading_pct, 6)
    naohs = np.linspace(min_naoh_pct, max_naoh_pct, 5)
    times = [0.0, 2.0, 4.0, 8.0]
    lengths = [8.0, 12.0, 16.0]

    candidates: list[OptimizationCandidate] = []

    for l in loadings:
        for n in naohs:
            for t in times:
                if n == 0.0 and t > 0.0:
                    continue
                for length in lengths:
                    inp_tensile = PredictionInput(
                        target="tensile_strength",
                        fibre_loading_wt_pct=float(l),
                        naoh_concentration_pct=float(n),
                        treatment_time_h=float(t),
                        fibre_length_mm=float(length),
                    )
                    res_tensile = predict_property(inp_tensile, allow_demo_benchmark=allow_demo_benchmark)
                    tensile_val = res_tensile.predicted_value or 0.0

                    inp_flex = PredictionInput(
                        target="flexural_strength",
                        fibre_loading_wt_pct=float(l),
                        naoh_concentration_pct=float(n),
                        treatment_time_h=float(t),
                        fibre_length_mm=float(length),
                    )
                    res_flex = predict_property(inp_flex, allow_demo_benchmark=allow_demo_benchmark)
                    flex_val = res_flex.predicted_value or 0.0

                    inp_impact = PredictionInput(
                        target="impact_resistance",
                        fibre_loading_wt_pct=float(l),
                        naoh_concentration_pct=float(n),
                        treatment_time_h=float(t),
                        fibre_length_mm=float(length),
                    )
                    res_impact = predict_property(inp_impact, allow_demo_benchmark=allow_demo_benchmark)
                    impact_val = res_impact.predicted_value or 0.0

                    inp_water = PredictionInput(
                        target="water_absorption",
                        fibre_loading_wt_pct=float(l),
                        naoh_concentration_pct=float(n),
                        treatment_time_h=float(t),
                        fibre_length_mm=float(length),
                    )
                    res_water = predict_property(inp_water, allow_demo_benchmark=allow_demo_benchmark)
                    water_val = res_water.predicted_value or 0.0

                    if water_val > max_water_absorption_pct:
                        continue

                    # Normalized utility score (higher is better)
                    norm_t = (tensile_val - 30.0) / 40.0
                    norm_f = (flex_val - 40.0) / 45.0
                    norm_i = (impact_val - 10.0) / 20.0
                    norm_w = max(0.0, (6.0 - water_val) / 5.5)

                    utility = (
                        weight_tensile * norm_t
                        + weight_flexural * norm_f
                        + weight_impact * norm_i
                        + weight_water_reduction * norm_w
                    )

                    candidates.append(
                        OptimizationCandidate(
                            fibre_loading_wt_pct=round(float(l), 1),
                            naoh_concentration_pct=round(float(n), 1),
                            treatment_time_h=round(float(t), 1),
                            fibre_length_mm=round(float(length), 1),
                            predicted_tensile_strength_mpa=round(tensile_val, 2),
                            predicted_flexural_strength_mpa=round(flex_val, 2),
                            predicted_impact_resistance_kj_m2=round(impact_val, 2),
                            predicted_water_absorption_pct=round(water_val, 2),
                            overall_utility_score=round(float(utility), 4),
                        )
                    )

    candidates.sort(key=lambda c: c.overall_utility_score, reverse=True)

    pareto_front: list[OptimizationCandidate] = []
    for c in candidates:
        is_dominated = False
        for other in candidates:
            if (
                other.predicted_tensile_strength_mpa >= c.predicted_tensile_strength_mpa
                and other.predicted_water_absorption_pct <= c.predicted_water_absorption_pct
                and (
                    other.predicted_tensile_strength_mpa > c.predicted_tensile_strength_mpa
                    or other.predicted_water_absorption_pct < c.predicted_water_absorption_pct
                )
            ):
                is_dominated = True
                break
        if not is_dominated:
            c.is_pareto_optimal = True
            pareto_front.append(c)

    disclaimer = (
        "DEMO BENCHMARK: Optimization recommendations are generated from simulated reference models. "
        "They do not constitute laboratory-validated formulations until physical coupons are "
        "fabricated, conditioned, and tested in accordance with ASTM/ISO standards."
    )

    return OptimizationResult(
        is_ready=True,
        status="demo_simulation" if allow_demo_benchmark else "evaluated",
        candidates_evaluated=len(candidates),
        top_candidates=candidates[:10],
        pareto_front=pareto_front[:10],
        objective_weights=weights,
        constraints=constraints,
        disclaimer=disclaimer,
        is_demo_benchmark=allow_demo_benchmark,
    )

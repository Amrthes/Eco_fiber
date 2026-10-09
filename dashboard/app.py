"""EcoFiber AI — Interactive Research & Demonstration Dashboard."""

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ecofiber_ai.audit import audit_datasets
from ecofiber_ai.eligibility import build_eligibility_audit
from ecofiber_ai.explainability import compute_feature_importances, sweep_parameter
from ecofiber_ai.inference import (
    PredictionInput,
    predict_property,
    validate_prediction_input,
)
from ecofiber_ai.literature import review_literature
from ecofiber_ai.optimization import optimize_formulation
from ecofiber_ai.readiness import build_readiness_report
from ecofiber_ai.schema import SUPPORTED_UNITS, TEST_TYPES
from ecofiber_ai.validation import validate_dataframe

PROJECT_ROOT = Path(__file__).parents[1]

st.set_page_config(
    page_title="EcoFiber AI — Sustainable Bio-Composites",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1b5e20;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4a5568;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f1f8e9;
        border-left: 5px solid #2e7d32;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    .warning-card {
        background-color: #fffde7;
        border-left: 5px solid #fbc02d;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    .error-card {
        background-color: #ffebee;
        border-left: 5px solid #c62828;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.image("https://raw.githubusercontent.com/feathericons/feather/master/icons/feather.svg", width=40)
    st.markdown("### 🌿 **EcoFiber AI**")
    st.caption("AI-Powered Bio-Composite Engineering from Invasive Plant Species (*Ipomoea carnea*)")
    st.divider()

    demo_mode = st.toggle(
        "⚡ Software Demo Mode",
        value=True,
        help="Enable physics-informed reference benchmark for interactive hackathon demonstration walkthrough. Real scientific dataset status remains strictly tracked.",
    )
    if demo_mode:
        st.info("ℹ️ **Demo Mode Active**: Simulated reference benchmark enabled for software review. Real scientific models remain gated.", icon="🧪")
    else:
        st.warning("⚠️ **Strict Real-Data Mode**: Gated predictions strictly enforced. Targets with insufficient verified real data will display 'Model Not Ready'.", icon="🛡️")

    st.divider()
    st.markdown("#### Scientific Safeguards")
    st.markdown("- 🔒 Minimum 12 compatible observations")
    st.markdown("- 🔒 Minimum 4 independent batches")
    st.markdown("- 🔒 Zero synthetic data leakage")
    st.markdown("- 🔒 Grouped holdout validation")

st.markdown('<div class="main-header">🌿 EcoFiber AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">AI-Powered Property Prediction, Scientific Evidence Audit & Sustainable Formulation Optimization for <i>Ipomoea carnea</i> Bio-Composites</div>',
    unsafe_allow_html=True,
)

tabs = st.tabs(
    [
        "🎯 Property Prediction",
        "🔬 Evidence & Readiness Audit",
        "💡 Explainability & Sensitivity",
        "⚙️ Formulation Optimizer",
        "🧪 Experimental Data Studio",
    ]
)

# ==========================================
# TAB 1: PROPERTY PREDICTION
# ==========================================
with tabs[0]:
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("1. Formulation Parameters")

        target_prop = st.selectbox(
            "Target Property",
            options=sorted(TEST_TYPES),
            format_func=lambda x: {
                "tensile_strength": "Tensile Strength (MPa)",
                "flexural_strength": "Flexural Strength (MPa)",
                "impact_resistance": "Impact Resistance (kJ/m²)",
                "water_absorption": "Water Absorption (%)",
            }.get(x, x),
        )

        c1, c2 = st.columns(2)
        with c1:
            fibre_loading = st.slider("Fibre Loading (wt%)", min_value=0.0, max_value=60.0, value=30.0, step=1.0)
            naoh_conc = st.slider("NaOH Treatment Conc (%)", min_value=0.0, max_value=15.0, value=4.0, step=0.5)
        with c2:
            treatment_time = st.slider("Treatment Time (hours)", min_value=0.0, max_value=24.0, value=4.0, step=0.5)
            fibre_length = st.slider("Fibre Length (mm)", min_value=1.0, max_value=30.0, value=10.0, step=1.0)

        with st.expander("Advanced Material & Fabrication Metadata"):
            fibre_species = st.selectbox("Fibre Species", ["Ipomoea carnea (Standard)", "Water hyacinth (Context)", "Bamboo (Context)"])
            matrix_type = st.selectbox("Polymer Matrix", ["epoxy EPR 174 + V-140 hardener", "polyester resin", "bio-phenolic resin"])
            fibre_form = st.selectbox("Fibre Form", ["short fibre", "unidirectional strands", "woven mat", "particulate"])
            fab_method = st.selectbox("Fabrication Method", ["hand lay-up with mould compaction", "compression moulding", "vacuum bagging"])

        input_obj = PredictionInput(
            target=target_prop,
            fibre_loading_wt_pct=fibre_loading,
            naoh_concentration_pct=naoh_conc,
            treatment_time_h=treatment_time,
            fibre_length_mm=fibre_length,
            fibre_type=fibre_species,
            matrix_type=matrix_type,
            fibre_form=fibre_form,
            fabrication_method=fab_method,
        )

        validation_check = validate_prediction_input(input_obj)
        if validation_check.warnings:
            for w in validation_check.warnings:
                st.warning(f"⚠️ {w}")

    with col2:
        st.subheader("2. Model Evaluation & Output")

        pred_res = predict_property(
            input_obj,
            project_root=PROJECT_ROOT,
            allow_demo_benchmark=demo_mode,
        )

        if pred_res.is_ready and pred_res.predicted_value is not None:
            if pred_res.is_demo_benchmark:
                st.markdown(
                    """
                    <div class="warning-card">
                        <b>🧪 DEMO BENCHMARK MODE (Simulated Reference)</b><br>
                        Generated for UI testing and workflow demonstration. Real scientific training gates remain active.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.metric(
                    label=f"Predicted {target_prop.replace('_', ' ').title()}",
                    value=f"{pred_res.predicted_value} {pred_res.predicted_unit}",
                )
            with res_col2:
                ci_text = f"[{pred_res.lower_bound_95}, {pred_res.upper_bound_95}] {pred_res.predicted_unit}" if pred_res.lower_bound_95 is not None else "Omitted (Simulated Mode)"
                st.metric(
                    label="95% Confidence Interval",
                    value=ci_text,
                )

            # Gauge Chart
            max_gauge = max(100.0, pred_res.predicted_value * 1.5)
            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=pred_res.predicted_value,
                    domain={"x": [0, 1], "y": [0, 1]},
                    title={"text": f"{pred_res.target.replace('_', ' ').title()} ({pred_res.predicted_unit})"},
                    gauge={
                        "axis": {"range": [0, max_gauge]},
                        "bar": {"color": "#2e7d32"},
                    },
                )
            )
            fig_gauge.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

            if pred_res.model_metrics:
                m_c1, m_c2, m_c3 = st.columns(3)
                m_c1.metric("Holdout MAE", f"{pred_res.model_metrics.get('mae', 'N/A')}")
                m_c2.metric("Holdout RMSE", f"{pred_res.model_metrics.get('rmse', 'N/A')}")
                m_c3.metric("Holdout R²", f"{pred_res.model_metrics.get('r2', 'N/A')}")

            with st.expander("Model Limitations & Scientific Notes", expanded=True):
                for lim in pred_res.limitations:
                    st.markdown(f"- 📌 {lim}")
        else:
            st.markdown(
                """
                <div class="error-card">
                    <h4>🔒 Model Not Ready (Scientific Gate Active)</h4>
                    <p>No verified model exists for this target. EcoFiber AI strictly prevents unvalidated predictions.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("**Reasons for Ineligibility:**")
            for r in pred_res.reasons_unready:
                st.markdown(f"- ❌ {r}")
            st.info("💡 Tip: Toggle 'Software Demo Mode' in the sidebar to simulate model outputs for demonstration.", icon="💡")

# ==========================================
# TAB 2: EVIDENCE & READINESS AUDIT
# ==========================================
with tabs[1]:
    st.subheader("🔬 Comprehensive Scientific Evidence & Readiness Audit")

    audit_rep = build_eligibility_audit(PROJECT_ROOT)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registered Literature Sources", audit_rep.total_registered_sources)
    c2.metric("Extracted Observations", audit_rep.total_normalized_observations)
    c3.metric("Accepted Compatible Observations", audit_rep.total_accepted_compatible_observations)
    c4.metric("Unready Targets", f"{audit_rep.unready_target_count} / 4")

    st.divider()

    st.markdown("### Target Readiness Matrix")
    t_data = []
    for t_name, t_summary in audit_rep.targets.items():
        t_data.append(
            {
                "Target Property": t_name,
                "Canonical Unit": t_summary.canonical_unit,
                "Raw Rows": t_summary.total_observations_found,
                "Accepted Compatible": t_summary.accepted_compatible_observations,
                "Required Compatible": ">= 12",
                "Independent Groups": t_summary.independent_groups,
                "Required Groups": ">= 4",
                "Readiness Status": "🟢 Ready" if t_summary.model_ready else "🔴 Not Ready",
            }
        )
    st.dataframe(pd.DataFrame(t_data), use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("### Registered Literature Sources (11 Studies)")
    src_df = pd.DataFrame(audit_rep.sources_summary)
    st.dataframe(
        src_df[["source_id", "title", "verification_status", "access_level", "review_status", "compatibility_category", "review_notes"]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.markdown("### Extracted Literature Observations (25 Records)")
    obs_data = [
        {
            "Record ID": r.record_id,
            "Source ID": r.source_id,
            "Property": r.test_type,
            "Value": r.measured_value,
            "Unit": r.measured_unit,
            "Fibre Species": r.fibre_type,
            "Extraction Type": r.extraction_type,
            "Status": "Eligible" if r.is_eligible else "Ineligible",
            "Reasons": "; ".join(r.reasons_ineligible) if r.reasons_ineligible else "Meets criteria",
        }
        for r in audit_rep.observation_records
    ]
    st.dataframe(pd.DataFrame(obs_data), use_container_width=True, hide_index=True)

    st.download_button(
        "📥 Download Eligibility Audit Report (JSON)",
        data=json.dumps(audit_rep.to_dict(), indent=2),
        file_name="eligibility_audit.json",
        mime="application/json",
    )

# ==========================================
# TAB 3: EXPLAINABILITY & SENSITIVITY
# ==========================================
with tabs[2]:
    st.subheader("💡 Feature Importance & Sensitivity Analysis")

    exp_target = st.selectbox(
        "Analyze Target Property",
        options=sorted(TEST_TYPES),
        key="exp_target_select",
    )

    exp_report = compute_feature_importances(exp_target, allow_demo_benchmark=demo_mode)

    if not exp_report.is_available:
        st.markdown(
            """
            <div class="error-card">
                <h4>🔒 Feature Importance Unavailable</h4>
                <p>Empirical feature importances cannot be calculated because no verified model is trained on real physical data. Toggle 'Software Demo Mode' in the sidebar to review literature-derived domain hypotheses.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="warning-card">
                <b>🧪 Literature Mechanistic Prior Hypotheses (Demonstration Reference)</b><br>
                {exp_report.disclaimer}
            </div>
            """,
            unsafe_allow_html=True,
        )
        imp_df = pd.DataFrame([asdict(i) for i in exp_report.importances])

        col_imp1, col_imp2 = st.columns([1.2, 1])
        with col_imp1:
            fig_imp = px.bar(
                imp_df,
                x="relative_importance",
                y="feature",
                orientation="h",
                title=f"Relative Feature Importance: {exp_target.replace('_', ' ').title()}",
                color="relative_importance",
                color_continuous_scale="Greens",
                labels={"relative_importance": "Relative Importance", "feature": "Parameter"},
            )
            fig_imp.update_layout(yaxis={"autorange": "reversed"}, height=320, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_imp, use_container_width=True)

        with col_imp2:
            st.markdown("#### Scientific Mechanisms")
            for i in exp_report.importances:
                st.markdown(f"**`{i.feature}`** ({i.effect_direction})")
                st.caption(i.scientific_mechanism)

    st.divider()

    st.markdown("### 1D Parameter Sensitivity Curves")
    sweep_param = st.selectbox(
        "Select Parameter to Sweep",
        options=["fibre_loading_wt_pct", "naoh_concentration_pct", "treatment_time_h", "fibre_length_mm"],
        format_func=lambda x: {
            "fibre_loading_wt_pct": "Fibre Loading (wt%)",
            "naoh_concentration_pct": "NaOH Treatment Concentration (%)",
            "treatment_time_h": "Treatment Duration (hours)",
            "fibre_length_mm": "Fibre Length (mm)",
        }.get(x, x),
    )

    ranges = {
        "fibre_loading_wt_pct": (0.0, 50.0),
        "naoh_concentration_pct": (0.0, 12.0),
        "treatment_time_h": (0.0, 24.0),
        "fibre_length_mm": (2.0, 30.0),
    }
    min_v, max_v = ranges[sweep_param]

    sweep_res = sweep_parameter(
        exp_target,
        sweep_param,
        min_v,
        max_v,
        steps=30,
        allow_demo_benchmark=demo_mode,
    )

    if not sweep_res.is_available:
        st.warning(f"⚠️ {sweep_res.disclaimer}")
    else:
        sweep_df = pd.DataFrame(
            {
                "Parameter Value": sweep_res.parameter_values,
                "Predicted Value": sweep_res.predicted_values,
            }
        )

        fig_sweep = px.line(
            sweep_df,
            x="Parameter Value",
            y="Predicted Value",
            markers=True,
            title=f"Sensitivity: Effect of {sweep_param} on {exp_target.replace('_', ' ').title()} ({sweep_res.target_unit})",
            labels={
                "Parameter Value": sweep_param,
                "Predicted Value": f"{exp_target.replace('_', ' ').title()} ({sweep_res.target_unit})",
            },
        )
        fig_sweep.update_traces(line_color="#2e7d32", line_width=3)
        fig_sweep.update_layout(height=380, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_sweep, use_container_width=True)
        st.caption(sweep_res.disclaimer)

# ==========================================
# TAB 4: FORMULATION OPTIMIZER
# ==========================================
with tabs[3]:
    st.subheader("⚙️ Multi-Objective Formulation Optimizer")
    st.caption("Balance mechanical performance (tensile, flexural, impact) against moisture absorption and chemical usage.")

    opt_c1, opt_c2 = st.columns([1, 1.2])

    with opt_c1:
        st.markdown("#### 1. Objective Weights")
        w_tensile = st.slider("Tensile Strength Weight", 0.0, 1.0, 0.4, 0.05)
        w_flex = st.slider("Flexural Strength Weight", 0.0, 1.0, 0.3, 0.05)
        w_impact = st.slider("Impact Resistance Weight", 0.0, 1.0, 0.1, 0.05)
        w_water = st.slider("Water Resistance Weight (Minimize Absorption)", 0.0, 1.0, 0.2, 0.05)

        st.markdown("#### 2. Constraints")
        max_water = st.slider("Maximum Allowable Water Absorption (%)", 1.0, 8.0, 4.0, 0.5)
        loading_range = st.slider("Allowed Fibre Loading Range (wt%)", 10.0, 45.0, (15.0, 35.0), 5.0)

        run_opt = st.button("🚀 Run Formulation Optimization", type="primary")

    with opt_c2:
        st.markdown("#### 3. Optimal Formulation Candidates")
        opt_res = optimize_formulation(
            weight_tensile=w_tensile,
            weight_flexural=w_flex,
            weight_impact=w_impact,
            weight_water_reduction=w_water,
            max_water_absorption_pct=max_water,
            min_fibre_loading_pct=loading_range[0],
            max_fibre_loading_pct=loading_range[1],
            allow_demo_benchmark=demo_mode,
        )

        if not opt_res.is_ready:
            st.markdown(
                f"""
                <div class="error-card">
                    <h4>🔒 Optimizer Unavailable</h4>
                    <p>{opt_res.disclaimer}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info(f"Evaluated {opt_res.candidates_evaluated} formulation combinations against constraints.")

            top_df = pd.DataFrame([c.to_dict() for c in opt_res.top_candidates])
            st.dataframe(
                top_df[
                    [
                        "fibre_loading_wt_pct",
                        "naoh_concentration_pct",
                        "treatment_time_h",
                        "fibre_length_mm",
                        "predicted_tensile_strength_mpa",
                        "predicted_flexural_strength_mpa",
                        "predicted_water_absorption_pct",
                        "overall_utility_score",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            fig_pareto = px.scatter(
                top_df,
                x="predicted_tensile_strength_mpa",
                y="predicted_water_absorption_pct",
                color="overall_utility_score",
                size="fibre_loading_wt_pct",
                hover_data=["naoh_concentration_pct", "treatment_time_h"],
                title="Pareto Trade-off: Tensile Strength vs Water Absorption",
                labels={
                    "predicted_tensile_strength_mpa": "Tensile Strength (MPa) → Higher is Better",
                    "predicted_water_absorption_pct": "Water Absorption (%) → Lower is Better",
                },
                color_continuous_scale="Viridis",
            )
            fig_pareto.update_layout(height=340, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_pareto, use_container_width=True)

            st.warning(f"⚠️ {opt_res.disclaimer}")

# ==========================================
# TAB 5: EXPERIMENTAL DATA STUDIO
# ==========================================
with tabs[4]:
    st.subheader("🧪 Experimental Data Collection & Validation Studio")
    st.caption("Upload newly measured physical laboratory datasets to run instant schema, unit, and duplicate validation.")

    uploaded_file = st.file_uploader("Upload Experimental Observation CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file, dtype="string", keep_default_na=False)
            st.write("#### Uploaded Data Preview", df_upload.head())

            report = validate_dataframe(df_upload, source_file=uploaded_file.name)

            if report.is_valid:
                st.success(f"✅ CSV is valid! {report.valid_record_count} valid records detected with 0 errors.", icon="✅")
            else:
                st.error(f"❌ Found {len(report.errors)} validation errors across {report.invalid_record_count} records.", icon="🚨")
                for err in report.errors:
                    st.markdown(f"- **[{err.code}]** {err.message} (Record: `{err.record_id or 'N/A'}`)")

            if report.warnings:
                st.warning(f"⚠️ {len(report.warnings)} warnings detected:")
                for warn in report.warnings:
                    st.markdown(f"- **[{warn.code}]** {warn.message}")

        except Exception as exc:
            st.error(f"Error parsing CSV: {exc}")
    else:
        st.info("ℹ️ Download templates from `data/templates/experimental_observations_template.csv` to format your physical measurements.")

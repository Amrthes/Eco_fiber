# EcoFiber AI — Hackathon Demonstration Script

This demo script walks through the end-to-end features of EcoFiber AI for judges, researchers, and hackathon reviewers.

---

## 1. Quick Start / Setup

From PowerShell in the repository root:

```powershell
# 1. Activate environment
.\.venv\Scripts\Activate.ps1

# 2. Run test suite to verify system integrity (65 passing tests)
python -m pytest -v

# 3. Launch interactive Streamlit dashboard
python -m ecofiber_ai dashboard
```

---

## 2. Walkthrough Steps

### Step 1: Scientific Integrity & Evidence Audit (Tab: "Evidence & Readiness Audit")
- **Action:** Open the **Evidence & Readiness Audit** tab in the dashboard (or run `python -m ecofiber_ai eligibility` in CLI).
- **Explanation:**
  - *"Notice that our dashboard shows exactly 11 registered literature sources, 25 normalized extracted observations, and 0 accepted compatible observations."*
  - *"Why are the targets marked 🔴 NOT READY? Because EcoFiber AI refuses to make unvalidated predictions. None of the available literature observations match pure Ipomoea carnea with verified full-text stats; our bamboo and water hyacinth records are preserved as context-only evidence."*
  - *"We have 4 targets (`tensile_strength`, `flexural_strength`, `impact_resistance`, `water_absorption`), each requiring >= 12 compatible observations and >= 4 independent batches before training is unlocked."*

---

### Step 2: Property Prediction & Readiness Gates (Tab: "Property Prediction")
- **Action:** Select **Tensile Strength (MPa)**.
- **Action 1 (Strict Mode):**
  - Toggle off "Software Demo Mode" in the sidebar.
  - Observe the clear **"Model Not Ready"** card detailing the exact scientific reasons why no model is fitted.
  - *"This demonstrates our core value proposition: Zero false claims, zero hallucinated data."*
- **Action 2 (Demo Benchmark Mode):**
  - Toggle on "Software Demo Mode" in the sidebar.
  - Adjust parameters: Fibre loading = **30 wt%**, NaOH conc = **4.0%**, Treatment time = **4.0 h**, Fibre length = **10.0 mm**.
  - Observe the predicted value (**63.0 MPa**), gauge chart, and clear note that confidence intervals and empirical holdout metrics are omitted until empirical calibration on laboratory data.
  - Note the clear banner: `[DEMO BENCHMARK MODE - Simulated Reference]` ensuring no evaluator confuses simulation with real scientific data.

---

### Step 3: Explainability & Mechanistic Insights (Tab: "Explainability & Sensitivity")
- **Action:** Navigate to the **Explainability & Sensitivity** tab.
- **Explanation:**
  - Note the clear banner: `🧪 Literature Mechanistic Prior Hypotheses (Demonstration Reference)` indicating these are qualitative domain hypotheses, not trained statistical coefficients.
  - Feature importance chart: Fibre loading (42%) and NaOH concentration (28%) dominate tensile performance.
  - Scientific mechanism: Alkalization dewaxes the fiber, removing amorphous hemicellulose and lignin, increasing aspect ratio and interfacial friction.
  - Sweep the **NaOH Concentration (%)** from 0% to 12%:
    - Point out the non-linear parabolic curve: strength rises from 0% to an optimum peak around 3-5% NaOH, then declines at >8% due to cellulose degradation and excessive pitting.

---

### Step 4: Multi-Objective Formulation Optimization (Tab: "Formulation Optimizer")
- **Action:** Navigate to the **Formulation Optimizer** tab.
- **Explanation:**
  - *"In engineering natural composites, the main challenge is that adding more plant fiber increases mechanical strength but also increases water absorption (hydrophilicity)."*
  - Set constraints: Maximum allowable water absorption = **4.0%**, Fibre loading range = **15% to 35%**.
  - Set objective weights: Tensile = 0.4, Flexural = 0.3, Water Resistance = 0.2, Impact = 0.1.
  - Click **Run Formulation Optimization**.
  - View the generated **Pareto Front scatter plot** and optimal formulation table.
  - Highlight the top recommended candidate: e.g., **31.0 wt% fibre, 4.0% NaOH, 4.0 h treatment**, achieving 78.8 MPa Tensile, 88.6 MPa Flexural, and 3.3% Water Absorption.
  - Emphasize the disclaimer: all optimal recommendations are model predictions requiring physical coupon testing.

---

### Step 5: Experimental Data Studio (Tab: "Experimental Data Studio")
- **Action:** Open the **Experimental Data Studio** tab.
- **Action:** Upload a test CSV or view validation diagnostics in real time.
- **Explanation:**
  - Shows how researchers in the lab can enter specimen-level measurements and immediately receive validation feedback regarding units, missing metadata, duplicate specimens, and target readiness.

---

## 3. Key CLI Commands Summary for Demo

```powershell
# Run data audit
python -m ecofiber_ai audit

# Run literature review
python -m ecofiber_ai literature review

# Run eligibility audit
python -m ecofiber_ai eligibility

# Run end-to-end readiness snapshot
python -m ecofiber_ai readiness

# Run experimental quality review
python -m ecofiber_ai experimental review data/templates/experimental_observations_template.csv

# Run baseline model evaluation (reports unready diagnostic when real data is insufficient)
python -m ecofiber_ai model --target tensile_strength

# Run property prediction in strict mode (reports unready)
python -m ecofiber_ai predict --target tensile_strength --fibre-loading 30.0 --naoh-conc 4.0

# Run property prediction in demo benchmark mode
python -m ecofiber_ai predict --target tensile_strength --fibre-loading 30.0 --naoh-conc 4.0 --demo-mode
```


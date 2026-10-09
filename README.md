# EcoFiber AI

**AI-Powered Prediction, Evidence Audit & Formulation Optimization for Sustainable Bio-Composites**

EcoFiber AI is a research-grade machine learning platform for analyzing, predicting, and optimizing composites fabricated using natural fibers extracted from *Ipomoea carnea*, an invasive weed.

The platform enforces strict scientific data provenance, separation of evidence categories, leakage-aware grouped cross-validation, and transparent readiness gates to ensure that predictions are scientifically defensible.

---

## Current Status & Scientific Summary

- **Literature Register:** 11 registered sources (8 metadata-verified, 1 abstract-inspected, 2 full-text inspected).
- **Normalized Observations:** 25 extracted literature observations (water-hyacinth and bamboo extractions preserved as context-only evidence).
- **Accepted Compatible Observations:** **0** (no pure *Ipomoea carnea* composite observations meet full-text verification and compatibility criteria).
- **Target Readiness:** All 4 targets (`tensile_strength`, `flexural_strength`, `impact_resistance`, `water_absorption`) are correctly reported as **NOT READY** under real scientific data gates (minimum 12 compatible observations, minimum 4 independent batches required).
- **Test Suite:** **65 automated tests passing** (100% test pass rate covering schema validation, eligibility audits, duplicate detection, leakage gates, inference bounds, explainability, multi-objective optimization, and Streamlit AppTest execution).

---

## Key Features

1. **Evidence Eligibility & Readiness Audit:** Automated gap analysis and readiness reporting across all target properties ([`docs/LITERATURE.md`](docs/LITERATURE.md) and [`docs/MODELING.md`](docs/MODELING.md)).
2. **Leakage-Aware Evaluation Engine:** Grouped holdout splitting (`GroupShuffleSplit`) preventing source and batch leakage between train and test sets.
3. **Property Prediction & Domain Validation:** Validates physical bounds, matrix compatibility, and enforces strict refusal when models are not verified.
4. **Explainability & Mechanistic Insights:** Quantifies feature importance and generates 1D sensitivity curves capturing chemical dewaxing vs cellulose degradation.
5. **Multi-Objective Formulation Optimizer:** Identifies Pareto-optimal formulation trade-offs balancing tensile/flexural strength against moisture absorption and chemical usage.
6. **Interactive Streamlit Dashboard:** Complete 5-tab web application for researchers, reviewers, and hackathon evaluation.

---

## Requirements

- Windows 10/11 or Linux / macOS
- Python 3.10, 3.11, or 3.12
- Dependencies: `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `plotly`, `streamlit`, `pytest`

---

## Quick Setup

From PowerShell in the repository root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Or run directly with the virtual environment's executable:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

---

## Running Automated Tests

Run the complete test suite (65 tests):

```powershell
python -m pytest -v
```

---

## CLI Commands

EcoFiber AI provides a comprehensive command-line interface:

### 1. Evidence Eligibility Audit
Generates human-readable Markdown (`data/processed/eligibility_audit.md`) and machine-readable JSON (`data/processed/eligibility_audit.json`):
```powershell
python -m ecofiber_ai eligibility
```

### 2. Dataset Inventory Audit
Inventories all research CSVs under `data/raw/` and `data/processed/`:
```powershell
python -m ecofiber_ai audit --format markdown
```

### 3. Literature Provenance Review
Validates bibliographic metadata, access status, and extraction types:
```powershell
python -m ecofiber_ai literature review
```

### 4. Experimental Quality Review
Validates specimen and batch metadata without modifying the raw CSV:
```powershell
python -m ecofiber_ai experimental review data/templates/experimental_observations_template.csv
```

### 5. End-to-End Readiness Snapshot
Summarizes readiness across all targets without training or modifying files:
```powershell
python -m ecofiber_ai readiness
```

### 6. Validate a Measurement CSV
Validates columns, numeric bounds, units, and duplicate identifiers:
```powershell
python -m ecofiber_ai validate data/raw/literature/literature_observations.csv
```

### 7. Baseline Model Evaluation
Evaluates grouped regression baseline or generates actionable diagnostic report when data is insufficient:
```powershell
python -m ecofiber_ai model --target tensile_strength
```

### 8. Property Prediction
Evaluate property prediction with readiness checks and domain validation:
```powershell
# Strict Real-Data Mode (reports unready status because real dataset gates are active)
python -m ecofiber_ai predict --target tensile_strength --fibre-loading 30.0 --naoh-conc 4.0 --treatment-time 4.0

# Software Walkthrough / Demo Benchmark Mode
python -m ecofiber_ai predict --target tensile_strength --fibre-loading 30.0 --naoh-conc 4.0 --treatment-time 4.0 --demo-mode
```

### 9. Launch Interactive Dashboard
Launches the full interactive Streamlit web application:
```powershell
python -m ecofiber_ai dashboard
```
Or directly:
```powershell
streamlit run dashboard/app.py
```

---

## Project Structure

```text
EcoFiber-AI/
├── dashboard/
│   └── app.py                      # Interactive Streamlit application (5 tabs)
├── data/
│   ├── raw/
│   │   ├── experimental/           # Physical laboratory test measurements
│   │   └── literature/             # Sourced publications & normalized extractions
│   │       ├── source_register.csv # 11 registered literature sources
│   │       └── literature_observations.csv # 25 normalized evidence rows
│   ├── extractions/                # Staged paper extraction bundles (WH, Bamboo)
│   ├── templates/                  # Laboratory observation & test log templates
│   └── processed/                  # Derived audit & validation reports (Git-ignored)
├── docs/
│   ├── ARCHITECTURE.md             # System architecture & Mermaid flowcharts
│   ├── DEMO_SCRIPT.md              # Hackathon demonstration walkthrough
│   ├── PRESENTATION_OUTLINE.md     # Pitch deck & presentation outline
│   ├── LITERATURE.md               # Literature review protocol & source analyses
│   ├── EXPERIMENTAL_PROTOCOL.md    # Physical laboratory testing & safety guide
│   └── MODELING.md                 # Grouped evaluation methodology & leakage controls
├── src/
│   └── ecofiber_ai/
│       ├── __init__.py
│       ├── __main__.py             # CLI entry point (validate, audit, readiness, eligibility, predict, dashboard)
│       ├── schema.py               # Canonical schema & supported units (MPa, kJ/m^2, %)
│       ├── validation.py           # Strict dataset validator & error reporting
│       ├── compatibility.py        # Non-binding compatibility comparison helper
│       ├── audit.py                # File inventory & readiness audit scanner
│       ├── literature.py           # Literature register & observation review
│       ├── experimental.py         # Experimental quality review & specimen check
│       ├── eligibility.py          # Evidence eligibility audit engine
│       ├── readiness.py            # Aggregated readiness report builder
│       ├── modeling.py             # Preprocessing & grouped evaluation (GroupShuffleSplit)
│       ├── inference.py            # Prediction engine, bounds check & 95% CI
│       ├── explainability.py       # Feature importance & sensitivity sweeps
│       └── optimization.py         # Multi-objective Pareto formulation optimizer
└── tests/                          # 65 unit & integration tests
```

---

## Research & Scientific Integrity Principles

1. **Zero Data Fabrication:** Missing measurements are never invented, imputed, or presented as experimental findings.
2. **Evidence-Type Segregation:** Graph estimates (`graph_estimate`) and unspecified statistics (`reported_value`) are preserved for provenance but blocked from entering model training.
3. **No Incompatible Species Pooling:** Water hyacinth and bamboo evidence are quarantined and never pooled with *Ipomoea carnea*.
4. **Grouped Leakage Prevention:** `GroupShuffleSplit` groups entire batches and publications to prevent data leakage between training and testing partitions.
5. **Transparent 'Not Ready' Reporting:** EcoFiber AI prioritizes scientific credibility: an unready status is always preferable to an unsupported prediction.

---

## Documentation & Deliverables

- 📘 [System Architecture & Data Pipeline](docs/ARCHITECTURE.md)
- 🎬 [Hackathon Demonstration Script](docs/DEMO_SCRIPT.md)
- 📊 [Presentation & Pitch Deck Outline](docs/PRESENTATION_OUTLINE.md)
- 📚 [Literature Review & Access Register](docs/LITERATURE.md)
- 🧪 [Experimental Testing Protocol](docs/EXPERIMENTAL_PROTOCOL.md)
- 📐 [Modeling Methodology & Leakage Controls](docs/MODELING.md)

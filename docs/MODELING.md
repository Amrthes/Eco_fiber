# Dataset audit and baseline methodology

## Source discovery and audit

`python -m ecofiber_ai audit` scans CSV files below:

- `data/raw/experimental/`
- `data/raw/literature/`
- `data/processed/`

These areas are reported independently. Files are never joined automatically.
`tests/fixtures/` is outside the scan roots and is never considered a
scientific dataset. Audit outputs default to `data/processed/dataset_audit.md`;
use `--format json` for machine-readable output.
The empty experiment entry templates live in `data/templates/`, outside raw
data discovery. For a real experimental CSV, use
`python -m ecofiber_ai experimental review <csv>` for record-level quality
statuses, unique specimen/batch counts, unit consistency, and missing
metadata. This review does not change the audit or model thresholds and never
edits the raw source. During modeling, only records marked `accepted` by this
experimental quality review are eligible; records needing review or rejected
by it are explicitly excluded.

The end-to-end non-training demonstration is:

```powershell
python -m ecofiber_ai readiness
```

It refreshes the linked audit, literature, and experimental quality reports
and produces `data/processed/readiness/readiness_report.md` and JSON. It does
not merge separate raw files, train a model, or create predictions.

For each file, the audit reports the record count, source type, values for
fibre/matrix/treatment/loading/length/property/unit fields, per-canonical-field
missing-value counts, duplicate record IDs and complete rows, and a
provenance-completeness count. Literature provenance requires a source ID,
material/test context, and at least one publication title or DOI/URL. A
potential target readiness status is structural, not scientific certification.

## Model input and inclusion rules

The CLI accepts one selected CSV under either raw source directory:

```powershell
python -m ecofiber_ai model --target tensile_strength
python -m ecofiber_ai model --target tensile_strength --csv data/raw/experimental/study.csv
```

Without `--csv`, discovery proceeds only when exactly one raw CSV exists.
Processed datasets, files outside raw source directories, records marked as
artificial/synthetic/test fixtures, and CSVs whose `source_type` conflicts
with their raw directory are refused.

Targets follow the schema's `test_type` names:

| Target | Accepted stored units |
|---|---|
| `tensile_strength` | `MPa` |
| `flexural_strength` | `MPa` |
| `impact_resistance` | `kJ/m^2`, `kJ/m²`, or `J/m` |
| `water_absorption` | `%` |

Only unit spelling aliases are normalized. There is no dimensional or scale
conversion between `J/m` and `kJ/m^2`. Use `--unit` to select one compatible
unit group if more than one is present; unsupported or invalid units are
excluded and counted.

The input must pass schema checks for each included row, have one source type,
and provide a single known fibre type, matrix type, and test standard for the
selected target observations. Literature observations need a publication
title or DOI/URL matching a verified source-register entry, and both the
register source and extracted observation must be explicitly marked `accepted`
and `directly comparable`. Duplicate IDs and exact duplicate records are
excluded. Unverified, rejected, pending, conditional, and context-only sources
cannot enter training.
Literature rows with `extraction_type` `graph_estimate`, `inferred`, or
`reported_value` (a numeric value whose statistic is unspecified) are also
evidence-only and excluded from training. Only `individual`, `reported_mean`,
and `reported_range` values may pass this evidence-type check; they remain
subject to all other source, compatibility, provenance, and grouped-readiness
gates.
The model does not combine separate CSVs or make an automatic compatibility
decision between publications.

Predictors are restricted to available fibre/treatment/fabrication features:
fibre type/form, matrix type, treatment method, NaOH concentration, treatment
time, fibre loading, fibre length, and fabrication method. Identifiers,
measured values from other properties, test standard, and target/property
labels are never predictors. Numeric missing values use median imputation;
categorical missing values use most-frequent imputation and one-hot encoding.
All preprocessing is fitted within the training partition.

## Leakage-aware evaluation

The first release requires at least 12 compatible target rows and 4 independent
groups. It groups by `(source_id, batch_id)` if all observations have batch IDs;
otherwise it groups by `source_id`. One deterministic
`GroupShuffleSplit(test_size=0.25, random_state=42)` holdout keeps each group
entirely in either train or test. The holdout must have at least 8 training and
3 test observations.

The comparison starts with a mean `DummyRegressor`, then linear regression;
random forest is included if the training subset contains at least 10 records.
The report gives MAE and RMSE. R² is emitted only when the holdout includes at
least two groups, at least two target values, and at least two observations.
The single grouped holdout is a screening estimate and does not establish
study-level generalization or support final model selection. Comparing models
on the same holdout is not a substitute for nested/grouped cross-validation
when selecting a final scientific model.

On success, the all-eligible-data mean `DummyRegressor` pipeline is saved under
`models/`; the comparison diagnostics are saved under
`data/processed/models/`. On failure, a JSON diagnostic is still saved and no
model artifact is written. Reports include excluded record identifiers (or a
row number when the identifier is missing) with exclusion reasons. These
generated outputs are Git-ignored.

## Current evidence and test data

The raw experimental directory contains no measurements. The literature
observation CSV contains 25 pending/rejected, context-only entries from two
supplied extraction bundles. The bamboo paper is full-text inspected, but its
values are graph estimates and its fibre is not Ipomoea carnea; the
water-hyacinth paper is also full-text inspected and its six text rows are
source-checked, but it is a different fibre species and remains context-only.
Its three unresolved text/Figure 6 conflicts and all graph estimates remain
ineligible. No source is accepted or eligible for training.
Therefore the workspace has no real usable observations, no reported model
metrics, and no trained scientific model. The model command returns an
insufficient-data diagnostic until source-verified, compatible records pass
the existing gates.

CSV fixtures under `tests/fixtures/` use artificial labels solely to test
validation and software behavior. Dataset discovery never searches that
directory; the modeling input resolver rejects paths outside raw data folders,
and fixture markers are additionally refused if copied into a raw folder.
Metrics produced in isolated unit tests, if any, are test assertions only and
must never be cited as scientific model performance.

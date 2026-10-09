# Experimental data collection protocol

## Scope and status

This document is a recording plan, not a report of completed laboratory work.
The project README documents the planned treatment groups as untreated fibre
(0% NaOH), 3% NaOH, and 5% NaOH, with approximately 30 wt% fibre loading.
These are planned conditions; confirm them with the supervisor and record the
actual preparation basis and measured formulation for every batch. No
experimental measurements are currently available.

The test standard, specimen geometry, conditioning, apparatus settings,
replicate count, cure schedule, and acceptance criteria must be selected and
approved by the responsible laboratory/supervisor for the actual material
system. This guide does not prescribe a substitute for the applicable current
ASTM/ISO method, equipment instructions, or laboratory safety procedure.

## Files and identifiers

Start from the empty header-only template
[`data/templates/experimental_observations_template.csv`](../data/templates/experimental_observations_template.csv).
Copy it to a new, uniquely named CSV under `data/raw/experimental/` only when
there are real measured results to record. Do not populate the template with
planned, illustrative, or guessed measurements.

The template includes the canonical observation schema followed by experimental
metadata extensions. One row represents one measured property for one
specimen and replicate. Use these identifiers consistently:

- `source_id`: stable experiment/study identifier.
- `batch_id`: independently prepared material batch.
- `specimen_id`: unique physical test coupon identifier.
- `replicate_id`: repeat/replicate test identifier where applicable.
- `record_id`: unique row/measurement identifier; do not reuse it.
- `measurement_source`: traceable laboratory notebook, instrument export, or
  source-file identifier. Do not store private credentials or sensitive data.

Record fibre species/form and preparation, matrix/resin identity, actual
fibre-loading basis, treatment, all relevant fabrication details, and test
standard/revision. If epoxy resin and hardener are used, record the actual
ratio and its basis in `resin_hardener_ratio`. Record curing temperature and
duration in `curing_temperature_c` and `curing_time_h`; keep other cure
conditions in `notes` or a referenced lab record. Record `measurement_date` in
ISO `YYYY-MM-DD` form.

The six schema-required columns are `record_id`, `source_type`, `source_id`,
`test_type`, `measured_value`, and `measured_unit`. For experimental rows,
`source_type` must be `experimental`. The quality review also flags missing
specimen/batch identifiers, fibre and matrix identity, treatment/loading,
fabrication/test standard, date, or traceable measurement source for review.
Unknown metadata must remain blank and be explained; do not infer it from the
planned design.

## Measurement recording

Record the method/standard exactly as used, including revision when available,
specimen dimensions, conditioning, equipment identity/calibration reference,
test date, and raw instrument-file/notebook location in the laboratory record.
These details are essential for interpreting comparability.

- **Tensile strength:** Follow the supervisor-approved tensile test method
  appropriate to the specimen and composite. Preserve the instrument's raw
  force/displacement output and the calculation inputs used to derive
  strength. Store `tensile_strength` in `MPa`.
- **Flexural strength:** Use the approved flexural method and record span,
  loading arrangement, specimen dimensions, and the actual calculation
  convention. Store `flexural_strength` in `MPa`.
- **Impact resistance:** Record the approved impact method, specimen notch
  state/geometry, impactor and apparatus settings, and the property definition.
  Store only the applicable unit (`kJ/m^2` or `J/m`) without assuming they are
  interchangeable; EcoFiber AI does not convert between them.
- **Water absorption:** Record the conditioning/drying procedure, immersion
  conditions, weighing timepoints, and percentage basis. Store
  `water_absorption` in `%`; state the basis/timepoint in `notes` or the
  linked lab record.

Use the canonical units enforced by the validator. Preserve original
instrument data and calculations separately; do not overwrite source exports.

## Failed tests, missing results, and corrections

Do not make an observation row with a fabricated value or a placeholder zero
for a result that was not measured. Record planned, failed, invalidated, or
missing tests in the separate empty
[`data/templates/experimental_test_log_template.csv`](../data/templates/experimental_test_log_template.csv)
and keep the failure reason and traceable notebook/source reference. Only
actual numeric observations belong in the observation CSV. If a recorded
measurement is later corrected, preserve the original source file, create a
new version/correction record with an explanation, and retain the audit trail;
never silently replace or delete the original measurement.

## Quality review and readiness

Run the structural validator and experimental quality review on a real
observation CSV:

```powershell
.\.venv\Scripts\python.exe -m ecofiber_ai validate data/raw/experimental/experiment_2026_10_09.csv
.\.venv\Scripts\python.exe -m ecofiber_ai experimental review data/raw/experimental/experiment_2026_10_09.csv
.\.venv\Scripts\python.exe -m ecofiber_ai audit
```

Validation writes a processed copy/report and does not filter the source. The
experimental review produces per-record `accepted`, `review`, or `rejected`
decisions and target readiness counts without modifying the input. Resolve
errors, duplicate measurement keys, conflicting replicate values, missing
metadata, and unit inconsistencies against the original laboratory records.
Keep experimental and literature files separate; the compatibility helper
flags differences but never authorizes automatic pooling.

The existing baseline modelling gates remain unchanged: at least 12 compatible
observations, 4 independent source/batch groups, sufficient grouped
train/test sizes, consistent property units, and required material/test
metadata. Passing a structural review does not establish scientific validity
or prove generalization. Do not fit a model until these requirements and
supervisor review are satisfied.

## Safety and oversight

NaOH handling, fibre processing, epoxy/hardener use, specimen fabrication,
mechanical testing, waste disposal, and equipment operation must follow the
institution's risk assessment, safety data sheets, approved laboratory
procedures, equipment manuals, and supervisor instructions. This software
guide is not a laboratory safety procedure.

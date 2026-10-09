# Research data guide

## Data availability

No experimental measurements are currently available. The literature source
register contains five DOI-backed records with bibliographic metadata checked,
one OpenAlex candidate whose indexed abstract was inspected, and two
user-supplied extraction sources that remain unverified and pending. The
canonical literature observation table contains normalized entries from the
water-hyacinth/epoxy workbook and bamboo/epoxy graph extraction, but every new
source is context-only and none is accepted for modelling. No paper full text
was independently inspected during that integration. See
`../docs/LITERATURE.md` for source mapping, evidence classifications,
limitations, and compatibility decisions.

Keep source data separate:

- `data/raw/experimental/` — measurements produced by the EcoFiber AI
  experimental programme.
- `data/raw/literature/` — manually curated observations transcribed from
  identifiable publications. Keep `source_register.csv` (bibliography/review)
  separate from `literature_observations.csv` (measured observations). Record
  the exact URL and ISO access date, and distinguish metadata, indexed
  abstract, and full-text inspection. Literature rows also carry the review
  extension fields `review_status`, `compatibility_category`,
  `extraction_type`, and `source_locator`; evidence-only extraction types are
  retained for traceability but blocked from modelling.
- `data/processed/` — validation copies and reports. This directory is
  excluded from version control by `.gitignore`.

The validator processes one CSV at a time. It does not combine experimental
and literature records, convert measurement values, impute missing metadata,
or remove questionable rows. The audit scans raw experimental, raw literature,
and processed CSV locations separately; test fixtures under `tests/fixtures/`
are not discovered or treated as scientific records.

## Experimental entry template and quality review

The empty template is
`data/templates/experimental_observations_template.csv`. It contains all
canonical columns plus experiment-specific fields for replicate, resin/hardener
ratio, curing temperature/time, measurement date, and a traceable measurement
source. It intentionally lives outside `data/raw/` so it is not mistaken for
an experimental dataset or selected by model input discovery. Copy it to a
new, uniquely named file under `data/raw/experimental/` only when recording
real measurements; never fill it with planned or illustrative values.

The companion
`data/templates/experimental_test_log_template.csv` is for planned, failed,
invalidated, or missing tests. A test log is not a measured observation and
must not be placed in the observation CSV as a zero or invented value.

Validate, review quality, and audit separately:

```powershell
python -m ecofiber_ai validate data/raw/experimental/experiment.csv
python -m ecofiber_ai experimental review data/raw/experimental/experiment.csv
python -m ecofiber_ai audit
```

The experimental review does not modify the raw file. It classifies rows as
accepted, review, or rejected; reports unit issues, duplicate records,
duplicate specimen/property/replicate measurements, conflicting values and
missing contextual metadata; and summarizes real observation, unique specimen
and batch-group counts per target. A `review` or `rejected` decision never
deletes or rewrites the source row. See
`../docs/EXPERIMENTAL_PROTOCOL.md` for identifier conventions, suggested
recording practice, failure logging, and the unchanged model readiness gates.

## Canonical observation schema

Use tidy observation format: **one row is one measured property for one
specimen/observation**. A specimen with tensile, flexural, impact, and
absorption results is represented by separate rows. Keep identifiers consistent
between rows to connect specimens and batches.

The following six columns must be present and populated for every row:

| Column | Meaning |
|---|---|
| `record_id` | Unique identifier for this property measurement. |
| `source_type` | Exactly `experimental` or `literature`. |
| `source_id` | Stable experiment/batch-study identifier or literature citation key. |
| `test_type` | One of `tensile_strength`, `flexural_strength`, `impact_resistance`, `water_absorption`. |
| `measured_value` | Finite numeric value of the measurement. |
| `measured_unit` | Property-appropriate unit listed below. |

Canonical optional metadata columns are:

| Column | Meaning and units |
|---|---|
| `publication_title` | Exact publication title; principally for literature records. |
| `doi_or_url` | DOI (prefer a DOI URL or DOI identifier) or stable publication URL; never guess. |
| `fibre_type` | Fibre identity as reported, including species where known. |
| `matrix_type` | Matrix/resin identity, e.g. epoxy or polyester as reported. |
| `treatment_method` | Treatment description as reported (e.g. NaOH where applicable). |
| `naoh_concentration_pct` | NaOH concentration in percent; validator allows 0–100. Record the source's concentration basis in `notes` if known. |
| `treatment_time_h` | Treatment duration in hours; must be non-negative. |
| `fibre_loading_wt_pct` | Fibre loading in weight percent; validator allows 0–100. |
| `fibre_length_mm` | Fibre length in millimetres; must be positive when supplied. |
| `fibre_form` | Reported form, such as continuous, chopped, or woven; retain the publication's terminology. |
| `fabrication_method` | Manufacturing/fabrication process as reported. |
| `test_standard` | Exact standard identifier and revision, if reported (e.g. ASTM/ISO designation). |
| `specimen_id` | Specimen identifier from the experimental notebook/source. |
| `batch_id` | Experimental batch identifier used to keep related specimens together. |
| `notes` | Context not represented elsewhere; do not use to replace known structured values. |

Blank optional fields are allowed and remain blank. Do not infer a value from
another publication or from the intended experimental design.

## Measurement units and basic constraints

| `test_type` | Accepted `measured_unit` | Measurement rule |
|---|---|---|
| `tensile_strength` | `MPa` | Greater than zero. |
| `flexural_strength` | `MPa` | Greater than zero. |
| `impact_resistance` | `kJ/m^2` (also `kJ/m²`) or `J/m` | Zero or greater. These unit forms are not automatically converted or assumed equivalent. |
| `water_absorption` | `%` | Zero or greater; the percentage basis/timepoint should be explained in `notes` or the source protocol. |

Optional numeric fields must be finite. NaOH concentration and fibre loading
must be within 0–100 inclusive; treatment time must be non-negative; fibre
length must be positive. The validator does not enforce a universal upper bound
for measured strength, impact, or absorption values. Implausible but numeric
measurements require scientific review rather than silent deletion.

## Import a real research dataset

1. Create a CSV in the appropriate raw source directory. Do not overwrite or
   edit the publication download/raw transcription during validation.
2. Use the column names above. Include all six required columns.
3. Assign a unique `record_id` to every property-level observation.
4. Set `source_type` to one value throughout the file.
5. For experimental work, use a stable `source_id` for the study/experiment
   and populate `specimen_id` and `batch_id` when available.
6. For literature, use a stable `source_id` (for example a local citation key)
   and enter the exact `publication_title` and verified `doi_or_url`. Record
   page/table/figure and transcription context in `notes` as useful. No DOI,
   title, or result should be invented.
7. Set the literature review extension fields only after evidence review.
   `reported_value` means the source does not state the statistic;
   `graph_estimate` and `inferred` are not verified measurements and are
   excluded from modelling.
8. Preserve reported units and test standards. If conversion is required, keep
   the source value and document the conversion method separately before
   adding an explicitly converted dataset.

## Validate

From the project root in PowerShell, after installing the package as described
in the main README:

```powershell
python -m ecofiber_ai validate data/raw/experimental/your_dataset.csv
```

For a literature source, point to that individual file instead:

```powershell
python -m ecofiber_ai validate data/raw/literature/your_dataset.csv
```

The command writes a copy of all input rows and a JSON validation report under
`data/processed/experimental/` or `data/processed/literature/`. Mixed or
unrecognized source types use `data/processed/unclassified/`. Use
`--output-dir <path>` to choose a different processed-output root. The raw
input is never modified. A command exit code of 0 means no validation errors;
warnings may still require attention. Exit code 1 means the report has errors;
exit code 2 means the CSV could not be read.

## Audit and baseline modelling

Create an inventory of real raw/processed CSVs, provenance completeness,
missing values, duplicates, available properties/units, and target readiness:

```powershell
python -m ecofiber_ai audit
python -m ecofiber_ai audit --format json
```

The Markdown report defaults to `data/processed/dataset_audit.md`; JSON uses
`dataset_audit.json`. Both are generated outputs, ignored by Git. The audit
does not scan test fixture directories and does not merge source files.

Baseline modeling accepts one reviewed raw source at a time:

```powershell
python -m ecofiber_ai model --target tensile_strength
python -m ecofiber_ai model --target tensile_strength --csv data/raw/experimental/study.csv
```

Allowed target names and units are `tensile_strength` (`MPa`),
`flexural_strength` (`MPa`), `impact_resistance` (`kJ/m^2` or `J/m`), and
`water_absorption` (`%`). `J/m` and `kJ/m^2` are distinct here and are not
converted. If incompatible accepted units coexist, select one with `--unit`.
The command never auto-loads processed CSVs or combines multiple raw source
files.

Run the read-only source/provenance report with:

```powershell
python -m ecofiber_ai literature review
```

It validates `source_register.csv`, detects duplicate source IDs/DOIs, checks
observation provenance, counts review classifications, and reports readiness
for each target. Only sources explicitly marked `accepted` and `directly
comparable` may be considered by the literature model workflow. A record in
the source register is not itself a measurement.

The modelling gate requires valid records, one source type, target units,
consistent and populated fibre/matrix/test-standard metadata, citation details
for literature observations, and at least 12 compatible target records across
4 independent groups. Grouping uses `source_id + batch_id` when all batch IDs
are present, otherwise `source_id`; specimens from one group cannot be split
between training and holdout. Insufficient data yield a report and no model.
See [../docs/MODELING.md](../docs/MODELING.md) for details and limitations.

All artificial fixture values are test-only examples. Never copy them into raw
research-data directories or use them as evidence, model inputs, or performance
results.

## Interpret findings

- **Errors** identify missing required fields/values, invalid identifiers,
  duplicate `record_id` values, unsupported property/unit combinations,
  non-finite or invalid numeric/text values, an empty dataset, and mixed source
  types. Fix them at the source transcription or correct the raw record
  deliberately, then rerun.
- **Warnings** flag absent optional columns/metadata, duplicate complete rows,
  or incomplete literature citations. Warnings do not remove records and do
  not certify a dataset as scientifically comparable.
- `valid_record_count` counts rows with no row-level errors. Dataset-level
  missing-column errors invalidate the dataset. All input records remain in
  the output copy even when invalid.
- Compare datasets with `compare_compatibility` in
  `ecofiber_ai.compatibility`. Differences in matrix, fibre type/form, test
  type/unit/standard, fabrication method, treatment, and loading are review
  flags—not an automatic compatibility verdict. In particular, epoxy and
  polyester data or measurements made using different test standards must not
  be pooled without a documented scientific review.

Validation is structural and does not confirm source authenticity, reproduce
the original analysis, or establish that measurements are scientifically
comparable.

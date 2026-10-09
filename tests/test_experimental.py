"""Experimental workflow tests use software-only rows created inside pytest."""

import csv
import json
from pathlib import Path

import pandas as pd

from ecofiber_ai.__main__ import main
from ecofiber_ai.experimental import (
    EXPERIMENTAL_METADATA_COLUMNS,
    review_experimental_csv,
)
from ecofiber_ai.schema import CANONICAL_COLUMNS


PROJECT = Path(__file__).parents[1]
TEMPLATE = PROJECT / "data" / "templates" / "experimental_observations_template.csv"
TEST_LOG_TEMPLATE = PROJECT / "data" / "templates" / "experimental_test_log_template.csv"


def software_record(**overrides):
    row = {column: "" for column in (*CANONICAL_COLUMNS, *EXPERIMENTAL_METADATA_COLUMNS)}
    row.update(
        {
            "record_id": "SOFTWARE-TEST-RECORD-001",
            "source_type": "experimental",
            "source_id": "SOFTWARE-TEST-STUDY",
            "fibre_type": "software test material",
            "matrix_type": "software test matrix",
            "treatment_method": "software test treatment",
            "naoh_concentration_pct": "3",
            "treatment_time_h": "1",
            "fibre_loading_wt_pct": "30",
            "fibre_length_mm": "10",
            "fibre_form": "software test form",
            "fabrication_method": "software test process",
            "test_type": "tensile_strength",
            "test_standard": "SOFTWARE-TEST-STANDARD",
            "measured_value": "100",
            "measured_unit": "MPa",
            "specimen_id": "SOFTWARE-TEST-SPECIMEN-001",
            "batch_id": "SOFTWARE-TEST-BATCH-001",
            "replicate_id": "1",
            "resin_hardener_ratio": "software test ratio",
            "curing_temperature_c": "25",
            "curing_time_h": "24",
            "measurement_date": "2026-01-01",
            "measurement_source": "software test notebook entry",
        }
    )
    row.update(overrides)
    return row


def save_rows(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_template_matches_canonical_schema_plus_experimental_metadata():
    with TEMPLATE.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))

    assert len(rows) == 1
    assert tuple(rows[0]) == (*CANONICAL_COLUMNS, *EXPERIMENTAL_METADATA_COLUMNS)
    with TEST_LOG_TEMPLATE.open(encoding="utf-8", newline="") as stream:
        log_rows = list(csv.reader(stream))
    assert len(log_rows) == 1
    assert "failure_reason" in log_rows[0]
    assert "result_status" in log_rows[0]


def test_valid_software_record_is_accepted_and_raw_input_is_unchanged(tmp_path):
    path = save_rows(tmp_path / "observations.csv", [software_record()])
    original = path.read_bytes()

    report = review_experimental_csv(path)

    assert report.accepted_count == 1
    assert report.review_count == report.rejected_count == 0
    assert report.target_readiness["tensile_strength"]["observation_count"] == 1
    assert report.target_readiness["tensile_strength"]["unique_specimen_count"] == 1
    assert path.read_bytes() == original


def test_invalid_numeric_and_unit_records_are_rejected(tmp_path):
    path = save_rows(
        tmp_path / "invalid.csv",
        [
            software_record(
                record_id="SOFTWARE-TEST-INVALID-001",
                measured_value="not-a-number",
                measured_unit="psi",
            )
        ],
    )

    report = review_experimental_csv(path)
    decision = report.decisions[0]

    assert decision.status == "rejected"
    assert any("invalid_numeric_value" in reason for reason in decision.reasons)
    assert any("unsupported_unit" in reason for reason in decision.reasons)


def test_duplicate_identifiers_and_conflicting_specimen_values_are_flagged(tmp_path):
    duplicate_id_path = save_rows(
        tmp_path / "duplicate_id.csv",
        [
            software_record(record_id="DUPLICATE-ID"),
            software_record(record_id="DUPLICATE-ID", specimen_id="OTHER-SPECIMEN"),
        ],
    )
    duplicate_id_report = review_experimental_csv(duplicate_id_path)
    assert duplicate_id_report.rejected_count == 2

    conflict_path = save_rows(
        tmp_path / "conflict.csv",
        [
            software_record(record_id="CONFLICT-001", replicate_id=""),
            software_record(
                record_id="CONFLICT-002",
                replicate_id="",
                measured_value="110",
            ),
        ],
    )
    conflict_report = review_experimental_csv(conflict_path)
    assert conflict_report.review_count == 2
    assert all(
        any("conflicting values" in reason for reason in decision.reasons)
        for decision in conflict_report.decisions
    )


def test_duplicate_specimen_measurement_is_rejected_and_missing_metadata_needs_review(
    tmp_path,
):
    duplicate_path = save_rows(
        tmp_path / "duplicate_measurement.csv",
        [
            software_record(record_id="DUPLICATE-MEASUREMENT-001"),
            software_record(record_id="DUPLICATE-MEASUREMENT-002"),
        ],
    )
    duplicate_report = review_experimental_csv(duplicate_path)
    assert duplicate_report.rejected_count == 2
    assert all(
        any("duplicate specimen/property" in reason for reason in decision.reasons)
        for decision in duplicate_report.decisions
    )

    incomplete_path = save_rows(
        tmp_path / "incomplete.csv",
        [
            software_record(
                record_id="INCOMPLETE-001",
                test_standard="",
                fabrication_method="",
                measurement_source="",
            )
        ],
    )
    incomplete_report = review_experimental_csv(incomplete_path)
    assert incomplete_report.review_count == 1
    assert incomplete_report.decisions[0].status == "review"


def test_inconsistent_compatible_units_and_invalid_cure_metadata_need_review(
    tmp_path,
):
    path = save_rows(
        tmp_path / "mixed_units.csv",
        [
            software_record(
                record_id="UNIT-CHECK-001",
                test_type="impact_resistance",
                measured_value="5",
                measured_unit="kJ/m^2",
                curing_time_h="-1",
            ),
            software_record(
                record_id="UNIT-CHECK-002",
                test_type="impact_resistance",
                measured_value="20",
                measured_unit="J/m",
                specimen_id="SOFTWARE-TEST-SPECIMEN-002",
                replicate_id="2",
            ),
        ],
    )

    report = review_experimental_csv(path)

    assert report.dataset_unit_consistency["impact_resistance"] == [
        "J/m",
        "kJ/m^2",
    ]
    assert report.review_count == 1
    assert report.rejected_count == 1
    assert any(
        "inconsistent units" in reason for decision in report.decisions for reason in decision.reasons
    )
    assert any(
        "curing_time_h" in reason
        for reason in report.decisions[0].reasons
    )


def test_empty_input_returns_not_ready_and_cli_writes_report(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text(",".join((*CANONICAL_COLUMNS, *EXPERIMENTAL_METADATA_COLUMNS)) + "\n")
    before = empty.read_bytes()
    output = tmp_path / "processed"

    result = main(
        [
            "experimental",
            "review",
            str(empty),
            "--output-dir",
            str(output),
        ]
    )

    report = json.loads(
        (output / "experimental_quality_review.json").read_text(encoding="utf-8")
    )
    assert result == 0
    assert report["record_count"] == 0
    assert all(
        readiness["status"] == "not ready"
        for readiness in report["target_readiness"].values()
    )
    assert empty.read_bytes() == before


def test_fixture_markers_are_rejected_as_research_data(tmp_path):
    path = save_rows(
        tmp_path / "synthetic_fixture.csv",
        [
            software_record(
                record_id="ARTIFICIAL-TEST-FIXTURE-001",
                notes="Artificial test fixture; not research data.",
            )
        ],
    )

    report = review_experimental_csv(path)

    assert report.rejected_count == 1
    assert any(
        "cannot be reviewed as research data" in reason
        for reason in report.decisions[0].reasons
    )

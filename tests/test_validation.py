"""Tests use artificial records only; they are not scientific observations."""

import json

import pandas as pd

from ecofiber_ai.__main__ import main
from ecofiber_ai.compatibility import compare_compatibility
from ecofiber_ai.validation import validate_dataframe, validate_csv


def artificial_record(**overrides):
    record = {
        "record_id": "ARTIFICIAL-001",
        "source_type": "experimental",
        "source_id": "ARTIFICIAL-TEST-STUDY",
        "publication_title": "",
        "doi_or_url": "",
        "fibre_type": "ARTIFICIAL TEST FIBRE",
        "matrix_type": "ARTIFICIAL TEST EPOXY",
        "treatment_method": "ARTIFICIAL TEST TREATMENT",
        "naoh_concentration_pct": "3",
        "treatment_time_h": "1",
        "fibre_loading_wt_pct": "30",
        "fibre_length_mm": "5",
        "fibre_form": "chopped",
        "fabrication_method": "ARTIFICIAL TEST METHOD",
        "test_type": "tensile_strength",
        "test_standard": "ARTIFICIAL TEST STANDARD",
        "measured_value": "10.5",
        "measured_unit": "MPa",
        "specimen_id": "ARTIFICIAL-SPECIMEN-001",
        "batch_id": "ARTIFICIAL-BATCH-001",
        "notes": "ARTIFICIAL TEST FIXTURE — not research data",
    }
    record.update(overrides)
    return record


def test_valid_artificial_record_has_no_errors():
    report = validate_dataframe(pd.DataFrame([artificial_record()]))

    assert report.is_valid
    assert report.record_count == 1
    assert report.valid_record_count == 1
    assert report.invalid_record_count == 0


def test_empty_dataset_is_reported_as_an_error():
    columns = list(artificial_record())
    report = validate_dataframe(pd.DataFrame(columns=columns))

    assert any(issue.code == "empty_dataset" for issue in report.errors)


def test_missing_required_columns_are_reported():
    report = validate_dataframe(pd.DataFrame([{"record_id": "ARTIFICIAL-001"}]))

    missing = {issue.column for issue in report.errors if issue.code == "missing_required_column"}
    assert {"source_type", "source_id", "test_type", "measured_value", "measured_unit"} <= missing
    assert not report.is_valid


def test_missing_source_identifier_is_an_error():
    report = validate_dataframe(
        pd.DataFrame([artificial_record(source_id="")])
    )

    assert any(
        issue.code == "missing_required_value" and issue.column == "source_id"
        for issue in report.errors
    )


def test_invalid_numeric_value_is_an_error():
    report = validate_dataframe(
        pd.DataFrame([artificial_record(measured_value="not-a-number")])
    )

    assert any(
        issue.code == "invalid_numeric_value" and issue.column == "measured_value"
        for issue in report.errors
    )


def test_duplicate_record_identifiers_are_an_error():
    report = validate_dataframe(
        pd.DataFrame(
            [
                artificial_record(record_id="ARTIFICIAL-DUPLICATE"),
                artificial_record(
                    record_id="ARTIFICIAL-DUPLICATE",
                    specimen_id="ARTIFICIAL-SPECIMEN-002",
                ),
            ]
        )
    )

    assert sum(issue.code == "duplicate_record_id" for issue in report.errors) == 1
    assert report.invalid_record_count == 1


def test_property_unit_mismatch_is_an_error():
    report = validate_dataframe(
        pd.DataFrame(
            [artificial_record(test_type="tensile_strength", measured_unit="%")]
        )
    )

    assert any(issue.code == "unsupported_unit" for issue in report.errors)


def test_csv_validation_preserves_raw_and_writes_a_report(tmp_path):
    raw_dir = tmp_path / "data" / "raw" / "experimental"
    raw_dir.mkdir(parents=True)
    input_path = raw_dir / "artificial_fixture.csv"
    original = pd.DataFrame([artificial_record()]).to_csv(index=False)
    input_path.write_text(original, encoding="utf-8")
    original_bytes = input_path.read_bytes()

    dataframe, report = validate_csv(input_path)
    assert report.is_valid
    assert len(dataframe) == 1
    assert input_path.read_bytes() == original_bytes

    report_path = tmp_path / "validation.json"
    report.write_json(report_path)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved_report["record_count"] == 1
    assert saved_report["is_valid"] is True


def test_cli_writes_processed_copy_and_report_without_changing_raw(tmp_path):
    raw_dir = tmp_path / "data" / "raw" / "experimental"
    raw_dir.mkdir(parents=True)
    input_path = raw_dir / "artificial_fixture.csv"
    input_path.write_text(
        pd.DataFrame([artificial_record()]).to_csv(index=False),
        encoding="utf-8",
    )
    original_bytes = input_path.read_bytes()
    output_dir = tmp_path / "processed"

    exit_code = main(
        [
            "validate",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    processed_dir = output_dir / "experimental"
    assert exit_code == 0
    assert input_path.read_bytes() == original_bytes
    assert (processed_dir / "artificial_fixture.validated.csv").is_file()
    report_file = processed_dir / "artificial_fixture.validation.json"
    assert json.loads(report_file.read_text(encoding="utf-8"))["is_valid"] is True


def test_compatibility_flags_epoxy_polyester_and_standard_difference():
    epoxy = pd.DataFrame(
        [artificial_record(matrix_type="epoxy", test_standard="ASTM-ARTIFICIAL-A")]
    )
    polyester = pd.DataFrame(
        [artificial_record(matrix_type="polyester", test_standard="ASTM-ARTIFICIAL-B")]
    )

    report = compare_compatibility(epoxy, polyester)
    statuses = {finding.field: finding.status for finding in report.findings}
    assert statuses["matrix_type"] == "difference"
    assert statuses["test_standard"] == "difference"
    assert report.automatic_merge_allowed is False

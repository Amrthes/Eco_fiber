"""Phase 3 tests use labelled artificial fixtures, never scientific observations."""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ecofiber_ai.__main__ import main
from ecofiber_ai.audit import audit_datasets, is_test_fixture
from ecofiber_ai.modeling import (
    ModelDataError,
    build_preprocessing_pipeline,
    discover_model_source,
    evaluate_grouped_models,
    run_baseline,
)
from ecofiber_ai.validation import load_csv, validate_dataframe

FIXTURES = Path(__file__).parent / "fixtures"


def test_checked_in_artificial_fixtures_validate_as_expected(tmp_path):
    cases = [
        ("valid_artificial.csv", True, None),
        ("missing_metadata_artificial.csv", False, "missing_required_value"),
        ("invalid_unit_artificial.csv", False, "unsupported_unit"),
        ("invalid_numeric_artificial.csv", False, "invalid_numeric_value"),
    ]
    originals = {
        filename: (FIXTURES / filename).read_bytes()
        for filename, _, _ in cases
    }

    for filename, expected_valid, expected_code in cases:
        path = FIXTURES / filename
        frame = load_csv(path)
        report = validate_dataframe(frame, source_file=str(path))
        assert report.is_valid is expected_valid
        if expected_code:
            assert any(issue.code == expected_code for issue in report.errors)

        output_dir = tmp_path / "processed"
        exit_code = main(
            [
                "validate",
                str(path),
                "--output-dir",
                str(output_dir),
            ]
        )
        assert exit_code == (0 if expected_valid else 1)
        processed = output_dir / "experimental"
        output_report = processed / f"{path.stem}.validation.json"
        output_csv = processed / f"{path.stem}.validated.csv"
        assert output_report.is_file()
        assert output_csv.is_file()
        saved_report = json.loads(output_report.read_text(encoding="utf-8"))
        if expected_code:
            assert any(
                issue["code"] == expected_code
                for issue in saved_report["errors"]
            )
        assert len(pd.read_csv(output_csv)) == 1

    assert {
        filename: (FIXTURES / filename).read_bytes()
        for filename, _, _ in cases
    } == originals


def test_validation_outputs_remain_partitioned_by_source_type(tmp_path):
    experimental = tmp_path / "experimental.csv"
    literature = tmp_path / "literature.csv"
    source_row = {
        "record_id": "ARTIFICIAL-SOURCE-PARTITION",
        "source_type": "experimental",
        "source_id": "ARTIFICIAL-STUDY",
        "test_type": "tensile_strength",
        "measured_value": "12",
        "measured_unit": "MPa",
        "publication_title": "",
        "doi_or_url": "",
    }
    pd.DataFrame([source_row]).to_csv(experimental, index=False)
    literature_row = {**source_row, "source_type": "literature"}
    literature_row["publication_title"] = "ARTIFICIAL TEST CITATION"
    pd.DataFrame([literature_row]).to_csv(literature, index=False)
    output = tmp_path / "processed"

    assert main(["validate", str(experimental), "--output-dir", str(output)]) == 0
    assert main(["validate", str(literature), "--output-dir", str(output)]) == 0
    assert (output / "experimental" / "experimental.validated.csv").exists()
    assert (output / "literature" / "literature.validated.csv").exists()


def test_dataset_audit_discovers_raw_and_processed_but_not_test_fixtures(tmp_path):
    raw_exp = tmp_path / "data" / "raw" / "experimental"
    raw_lit = tmp_path / "data" / "raw" / "literature"
    processed = tmp_path / "data" / "processed"
    fixture_dir = tmp_path / "tests" / "fixtures"
    for directory in (raw_exp, raw_lit, processed, fixture_dir):
        directory.mkdir(parents=True)
    shutil.copy(FIXTURES / "valid_artificial.csv", raw_exp / "artificial.csv")
    shutil.copy(FIXTURES / "missing_metadata_artificial.csv", raw_lit / "artificial.csv")
    shutil.copy(FIXTURES / "valid_artificial.csv", processed / "processed_copy.csv")
    shutil.copy(FIXTURES / "valid_artificial.csv", fixture_dir / "ignored.csv")

    audit = audit_datasets(tmp_path)

    assert audit.csv_file_count == 3
    assert audit.raw_experimental_csv_count == 1
    assert audit.raw_literature_csv_count == 1
    assert audit.processed_csv_count == 1
    assert all("tests" not in item.path for item in audit.files)
    experimental_audit = next(item for item in audit.files if item.area == "raw_experimental")
    assert experimental_audit.record_count == 1
    assert experimental_audit.test_fixture_marked
    assert experimental_audit.available_values["fibre_type"] == ["ARTIFICIAL-FIBRE"]
    assert experimental_audit.provenance_complete_records == 1
    assert not experimental_audit.modelling_readiness["tensile_strength"]["eligible"]
    literature_audit = next(item for item in audit.files if item.area == "raw_literature")
    assert literature_audit.provenance_incomplete_records == 1
    assert "No real raw observations" in audit.real_dataset_status
    report_path = tmp_path / "audit.md"
    audit.write_markdown(report_path)
    assert "not ready" in report_path.read_text(encoding="utf-8")


def test_audit_reports_duplicate_ids_missing_metadata_and_empty_repository(tmp_path):
    raw = tmp_path / "data" / "raw" / "experimental"
    raw.mkdir(parents=True)
    duplicate_records = pd.DataFrame(
        [
            {
                "record_id": "ARTIFICIAL-DUPLICATE",
                "source_type": "experimental",
                "source_id": "ARTIFICIAL-STUDY",
                "test_type": "tensile_strength",
                "measured_value": "10",
                "measured_unit": "MPa",
            },
            {
                "record_id": "ARTIFICIAL-DUPLICATE",
                "source_type": "experimental",
                "source_id": "ARTIFICIAL-STUDY",
                "test_type": "tensile_strength",
                "measured_value": "11",
                "measured_unit": "MPa",
            },
        ]
    )
    duplicate_records.to_csv(raw / "duplicates.csv", index=False)
    audit = audit_datasets(tmp_path)
    item = audit.files[0]
    assert item.duplicate_record_ids == 2
    assert item.missing_value_counts["fibre_type"] == 2
    assert item.provenance_incomplete_records == 2

    empty_audit = audit_datasets(tmp_path / "empty")
    assert empty_audit.csv_file_count == 0
    assert "empty" in empty_audit.real_dataset_status
    assert "No CSV datasets" in empty_audit.to_markdown()


def test_audit_cli_writes_readable_report_and_help(capsys, tmp_path):
    output = tmp_path / "reports"
    assert main(["audit", "--project-root", str(tmp_path), "--output-dir", str(output)]) == 0
    assert (output / "dataset_audit.md").is_file()
    assert "No real raw observations found" in capsys.readouterr().out

    with pytest.raises(SystemExit) as help_exit:
        main(["audit", "--help"])
    assert help_exit.value.code == 0
    assert "--format" in capsys.readouterr().out


def test_audit_json_serializes_boolean_fixture_markers(tmp_path):
    raw = tmp_path / "data" / "raw" / "literature"
    raw.mkdir(parents=True)
    pd.DataFrame(
        [{"source_type": "literature", "notes": "Source description."}]
    ).to_csv(raw / "observations.csv", index=False)

    audit = audit_datasets(tmp_path)
    destination = audit.write_json(tmp_path / "reports" / "dataset_audit.json")

    report = json.loads(destination.read_text(encoding="utf-8"))
    assert report["files"][0]["test_fixture_marked"] is False


def test_preprocessor_handles_numeric_categorical_and_missing_values():
    frame = pd.DataFrame(
        {
            "naoh_concentration_pct": [0.0, np.nan, 5.0],
            "fibre_type": ["ARTIFICIAL-FIBRE-A", None, "ARTIFICIAL-FIBRE-B"],
        }
    )
    pipeline = build_preprocessing_pipeline(
        ["naoh_concentration_pct", "fibre_type"]
    )
    transformed = pipeline.fit_transform(frame)

    assert transformed.shape[0] == 3
    assert transformed.shape[1] >= 3
    assert np.isfinite(transformed.toarray() if hasattr(transformed, "toarray") else transformed).all()


def test_grouped_model_evaluation_is_reproducible_on_test_only_rows():
    frame = pd.DataFrame(
        {
            "naoh_concentration_pct": [float(i % 6) for i in range(12)],
            "fibre_type": [
                "ARTIFICIAL-FIBRE-A" if i % 2 else "ARTIFICIAL-FIBRE-B"
                for i in range(12)
            ],
        }
    )
    frame.loc[3, "naoh_concentration_pct"] = np.nan
    frame.loc[7, "fibre_type"] = None
    targets = pd.Series([10.0 + i * 0.25 for i in range(12)])
    groups = pd.Series([f"ARTIFICIAL-BATCH-{i // 3}" for i in range(12)])
    features = ["naoh_concentration_pct", "fibre_type"]

    first = evaluate_grouped_models(frame, targets, groups, features)
    second = evaluate_grouped_models(frame, targets, groups, features)

    assert first[:3] == second[:3]
    assert first[0].keys() == {"dummy_mean", "linear_regression"}
    assert first[2] >= 3


def test_model_refuses_missing_real_data_and_writes_diagnostic(tmp_path):
    reports = tmp_path / "reports"
    result = run_baseline(
        "tensile_strength",
        project_root=tmp_path,
        output_dir=reports,
        model_dir=tmp_path / "models",
    )

    assert not result.trained
    assert "No raw scientific CSVs" in result.message
    assert Path(result.report_path).is_file()
    saved = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert saved["status"] == "insufficient_data"
    assert saved["metrics"] == {}
    assert not (tmp_path / "models").exists()


def test_model_discovery_ignores_literature_bibliography_register(tmp_path):
    raw_literature = tmp_path / "data" / "raw" / "literature"
    raw_literature.mkdir(parents=True)
    register = raw_literature / "source_register.csv"
    register.write_text("source_id,title\n", encoding="utf-8")
    observations = raw_literature / "literature_observations.csv"
    observations.write_text("record_id,source_type,source_id,test_type,measured_value,measured_unit\n", encoding="utf-8")

    assert discover_model_source(tmp_path) == observations.resolve()


def test_model_cannot_discover_fixtures_or_use_test_marked_raw_data(tmp_path):
    fixture = FIXTURES / "valid_artificial.csv"
    with pytest.raises(ModelDataError, match="inside data/raw"):
        discover_model_source(tmp_path, fixture)

    raw = tmp_path / "data" / "raw" / "experimental"
    raw.mkdir(parents=True)
    marked_raw = raw / "artificial_fixture.csv"
    shutil.copy(fixture, marked_raw)
    with pytest.raises(ModelDataError, match="fixture markers"):
        run_baseline("tensile_strength", project_root=tmp_path)


def test_fixture_detection_does_not_flag_scientific_synthetic_resin_description():
    legitimate = pd.DataFrame(
        {
            "record_id": ["IC-REAL-001"],
            "source_id": ["REAL-STUDY-01"],
            "notes": ["Synthetic epoxy matrix, tested using the reported protocol."],
        }
    )
    artificial = pd.DataFrame(
        {
            "record_id": ["ARTIFICIAL-FIXTURE-001"],
            "source_id": ["TEST-STUDY"],
            "notes": ["Artificial test fixture only."],
        }
    )

    assert not is_test_fixture(legitimate, "research.csv")
    assert is_test_fixture(artificial, "research.csv")


def test_model_cli_help_and_target_error(capsys):
    with pytest.raises(SystemExit) as help_exit:
        main(["model", "--help"])
    assert help_exit.value.code == 0
    assert "--target" in capsys.readouterr().out
    with pytest.raises(SystemExit) as invalid_exit:
        main(["model", "--target", "strength"])
    assert invalid_exit.value.code == 2

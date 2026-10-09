"""Readiness and modelling-gate tests use isolated software-only records."""

import json
import shutil
from pathlib import Path

import pandas as pd

from ecofiber_ai.__main__ import main
from ecofiber_ai.experimental import EXPERIMENTAL_METADATA_COLUMNS
from ecofiber_ai.literature import SOURCE_REGISTER_COLUMNS
from ecofiber_ai.modeling import run_baseline
from ecofiber_ai.readiness import build_readiness_report
from ecofiber_ai.schema import CANONICAL_COLUMNS, TEST_TYPES


PROJECT = Path(__file__).parents[1]


def empty_project(root):
    literature = root / "data" / "raw" / "literature"
    experimental = root / "data" / "raw" / "experimental"
    templates = root / "data" / "templates"
    literature.mkdir(parents=True)
    experimental.mkdir(parents=True)
    templates.mkdir(parents=True)
    (literature / "source_register.csv").write_text(
        ",".join(SOURCE_REGISTER_COLUMNS) + "\n",
        encoding="utf-8",
    )
    observation_columns = (
        *CANONICAL_COLUMNS,
        "review_status",
        "compatibility_category",
        "extraction_type",
        "source_locator",
    )
    (literature / "literature_observations.csv").write_text(
        ",".join(observation_columns) + "\n",
        encoding="utf-8",
    )
    shutil.copy(
        PROJECT / "data" / "templates" / "experimental_observations_template.csv",
        templates / "experimental_observations_template.csv",
    )
    return literature


def software_observation(**overrides):
    row = {
        field: ""
        for field in (*CANONICAL_COLUMNS, *EXPERIMENTAL_METADATA_COLUMNS)
    }
    row.update(
        {
            "record_id": "RECORD-QA-001",
            "source_type": "experimental",
            "source_id": "STUDY-QA-001",
            "fibre_type": "QA fibre",
            "matrix_type": "QA epoxy",
            "treatment_method": "alkali treatment",
            "naoh_concentration_pct": "3",
            "treatment_time_h": "1",
            "fibre_loading_wt_pct": "30",
            "fibre_length_mm": "10",
            "fibre_form": "chopped",
            "fabrication_method": "hand lay-up",
            "test_type": "tensile_strength",
            "test_standard": "QA-TEST-METHOD",
            "measured_value": "100",
            "measured_unit": "MPa",
            "specimen_id": "SPECIMEN-QA-001",
            "batch_id": "BATCH-QA-001",
            "replicate_id": "1",
            "resin_hardener_ratio": "2:1 by mass",
            "curing_temperature_c": "25",
            "curing_time_h": "24",
            "measurement_date": "2026-10-09",
            "measurement_source": "notebook page QA-001",
        }
    )
    row.update(overrides)
    return row


def test_empty_readiness_report_reports_every_target_unavailable(tmp_path):
    raw_literature = empty_project(tmp_path)
    raw_before = {
        path: path.read_bytes()
        for path in raw_literature.iterdir()
    }

    report = build_readiness_report(tmp_path)

    assert report.demo_status.endswith("no target is ready for a model request.")
    assert report.model_training_performed is False
    assert report.experimental_files == []
    assert report.literature_summary == {
        "sources_discovered": 0,
        "metadata_verified": 0,
        "abstract_inspected": 0,
        "full_text_inspected": 0,
        "sources_accepted": 0,
        "observation_count": 0,
        "provenance_complete_observations": 0,
    }
    assert set(report.targets) == set(TEST_TYPES)
    for target, item in report.targets.items():
        assert item["model_request_candidate"] is False
        assert item["experimental"]["observation_count"] == 0
        assert item["experimental"]["accepted_observation_count"] == 0
        assert item["literature"]["observation_count"] == 0
        assert item["literature"]["accepted_compatible_count"] == 0
        assert any("no raw experimental observations" in reason for reason in item["reasons"])
        assert "not ready" in report.to_markdown()
    assert {path: path.read_bytes() for path in raw_literature.iterdir()} == raw_before


def test_readiness_cli_writes_traceable_reports_and_preserves_raw_sources(
    tmp_path, capsys
):
    raw_literature = empty_project(tmp_path)
    raw_before = {
        path: path.read_bytes()
        for path in raw_literature.iterdir()
    }
    output = tmp_path / "reports"

    exit_code = main(
        [
            "readiness",
            "--project-root",
            str(tmp_path),
            "--output-dir",
            str(output),
        ]
    )

    assert exit_code == 0
    assert "no target is ready" in capsys.readouterr().out
    report_path = output / "readiness_report.json"
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = (output / "readiness_report.md").read_text(encoding="utf-8")
    assert saved["model_training_performed"] is False
    assert saved["audit_report"] == "data\\processed\\dataset_audit.md"
    assert saved["literature_report"] == (
        "data\\processed\\literature-review\\literature_review.md"
    )
    assert "no prediction was generated" in markdown.lower()
    assert "no model was trained" in markdown.lower()
    assert {path: path.read_bytes() for path in raw_literature.iterdir()} == raw_before
    assert (tmp_path / saved["audit_report"]).is_file()
    assert (tmp_path / saved["literature_report"]).is_file()


def test_model_does_not_use_experimental_records_needing_quality_review(tmp_path):
    raw = tmp_path / "data" / "raw" / "experimental"
    raw.mkdir(parents=True)
    record = software_observation(measurement_source="")
    csv_path = raw / "study.csv"
    pd.DataFrame([record]).to_csv(csv_path, index=False)
    before = csv_path.read_bytes()

    result = run_baseline(
        "tensile_strength",
        project_root=tmp_path,
        csv_path=csv_path,
        output_dir=tmp_path / "reports",
        model_dir=tmp_path / "models",
    )

    assert result.trained is False
    assert result.status == "insufficient_data"
    assert result.eligible_record_count == 0
    assert result.metrics == {}
    assert result.model_path is None
    assert result.excluded_reasons[
        "experimental quality review did not accept the record"
    ] == 1
    assert any(
        any("measurement_source" in reason for reason in item["reasons"])
        for item in result.excluded_records
    )
    assert csv_path.read_bytes() == before
    assert not (tmp_path / "models").exists()


def test_incompatible_units_cannot_bypass_quality_or_model_gates(tmp_path):
    raw = tmp_path / "data" / "raw" / "experimental"
    raw.mkdir(parents=True)
    records = [
        software_observation(
            record_id="IMPACT-QA-001",
            test_type="impact_resistance",
            measured_value="5",
            measured_unit="kJ/m^2",
        ),
        software_observation(
            record_id="IMPACT-QA-002",
            specimen_id="SPECIMEN-QA-002",
            replicate_id="2",
            test_type="impact_resistance",
            measured_value="5000",
            measured_unit="J/m",
        ),
    ]
    csv_path = raw / "impact.csv"
    pd.DataFrame(records).to_csv(csv_path, index=False)

    result = run_baseline(
        "impact_resistance",
        project_root=tmp_path,
        csv_path=csv_path,
        output_dir=tmp_path / "reports",
        model_dir=tmp_path / "models",
    )

    assert result.trained is False
    assert result.status == "insufficient_data"
    assert result.eligible_record_count == 0
    assert result.metrics == {}
    assert result.model_path is None
    assert result.excluded_reasons[
        "experimental quality review did not accept the record"
    ] == 2
    assert not (tmp_path / "models").exists()


def test_readiness_cli_help_and_empty_model_request_message(capsys, tmp_path):
    import pytest

    with pytest.raises(SystemExit) as help_exit:
        main(["readiness", "--help"])
    assert help_exit.value.code == 0
    assert "--output-dir" in capsys.readouterr().out

    exit_code = main(
        [
            "model",
            "--target",
            "tensile_strength",
            "--project-root",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "model-reports"),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No raw scientific CSVs" in captured.out
    assert "No prediction or model will be produced" in captured.out

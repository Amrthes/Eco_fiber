"""Literature workflow tests use isolated software-only synthetic records."""

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from ecofiber_ai.__main__ import main
from ecofiber_ai.literature import (
    MODEL_ELIGIBLE_EXTRACTION_TYPES,
    SOURCE_REGISTER_COLUMNS,
    accepted_directly_comparable_source_ids,
    review_literature,
    validate_source_register,
)
from ecofiber_ai.modeling import run_baseline

PROJECT = Path(__file__).parents[1]
LITERATURE = PROJECT / "data" / "raw" / "literature"


def synthetic_source(**overrides):
    source = {column: "" for column in SOURCE_REGISTER_COLUMNS}
    source.update(
        {
            "source_id": "UNITTEST-SOURCE-001",
            "title": "Software-only synthetic source record",
            "authors": "",
            "publication_year": "2026",
            "journal": "",
            "doi": "",
            "url": "",
            "metadata_source": "test fixture",
            "access_level": "metadata_only",
            "fibre_type": "test material",
            "matrix_type": "test matrix",
            "compatibility_category": "context only",
            "verification_status": "unverified",
            "review_status": "pending",
            "review_notes": "Synthetic unit-test fixture, not a publication.",
            "extraction_confidence": "not assessed; synthetic test fixture",
            "access_url": "https://example.invalid/software-only-fixture",
            "access_date": "2026-01-01",
        }
    )
    source.update(overrides)
    return source


def test_checked_in_source_register_has_expected_schema_and_verified_metadata():
    register = pd.read_csv(LITERATURE / "source_register.csv", dtype="string").fillna("")

    assert tuple(register.columns) == SOURCE_REGISTER_COLUMNS
    assert not validate_source_register(register)
    assert register["verification_status"].eq("metadata_verified").sum() == 8
    assert register["verification_status"].eq("abstract_inspected").sum() == 1
    assert register["verification_status"].eq("full_text_inspected").sum() == 2
    assert register["verification_status"].eq("unverified").sum() == 0
    assert register["review_status"].eq("pending").sum() == 9
    candidate = register.loc[register["source_id"] == "LIT-IC-2013-CANDIDATE"].iloc[0]
    assert candidate["verification_status"] == "abstract_inspected"
    assert candidate["review_status"] == "rejected"
    alert_record = register.loc[register["source_id"] == "LIT-IC-1988"].iloc[0]
    assert alert_record["review_status"] == "rejected"
    assert alert_record["compatibility_category"] == "rejected"
    assert set(register["compatibility_category"]) == {
        "context only",
        "conditionally comparable",
        "rejected",
    }
    assert accepted_directly_comparable_source_ids(
        LITERATURE / "source_register.csv"
    ) == set()
    assert register["access_url"].astype(bool).all()
    assert register["access_date"].eq("2026-10-09").all()
    expected_verification = {
        "WH-EPOXY-SULARDJAKA-2023": "full_text_inspected",
        "BAMBOO-EPOXY-RAMARAO-2018": "full_text_inspected",
    }
    for source_id, verification_status in expected_verification.items():
        source = register.loc[register["source_id"] == source_id].iloc[0]
        assert source["verification_status"] == verification_status
        assert source["review_status"] == "pending"
        assert source["compatibility_category"] == "context only"
        if source_id == "WH-EPOXY-SULARDJAKA-2023":
            assert "Zenodo record 7746959" in source["review_notes"]
            assert "Figure 6" in source["review_notes"]
            assert "unresolved" in source["review_notes"]
        else:
            assert "graph estimates" in source["review_notes"]
            assert "visually re-read" in source["review_notes"]


def test_source_register_requires_valid_access_url_and_date():
    register = pd.DataFrame(
        [
            synthetic_source(
                verification_status="metadata_verified",
                doi="10.1234/unit.test",
                access_url="not-a-url",
                access_date="2026-13-42",
            )
        ]
    )

    codes = {issue.code for issue in validate_source_register(register)}

    assert "invalid_access_url" in codes
    assert "invalid_access_date" in codes


def test_source_register_reports_missing_provenance_and_invalid_review_values():
    register = pd.DataFrame(
        [
            synthetic_source(
                source_id="",
                title="",
                access_url="",
                access_date="",
                verification_status="metadata_verified",
                review_status="accepted",
                compatibility_category="rejected",
            )
        ]
    )

    issues = validate_source_register(register)
    codes = {issue.code for issue in issues}

    assert "missing_register_value" in codes
    assert "missing_verified_identifier" in codes
    assert "inconsistent_acceptance" in codes


def test_source_register_detects_duplicate_ids_and_duplicate_dois():
    same_doi = "10.1234/unit.test"
    register = pd.DataFrame(
        [
            synthetic_source(source_id="DUPLICATE", doi=same_doi),
            synthetic_source(source_id="DUPLICATE", doi=f"https://doi.org/{same_doi}"),
        ]
    )

    issues = validate_source_register(register)
    codes = [issue.code for issue in issues]

    assert codes.count("duplicate_source_id") == 2
    assert codes.count("duplicate_paper") == 2


def test_unverified_source_cannot_be_model_eligible():
    register = pd.DataFrame(
        [
            synthetic_source(
                verification_status="unverified",
                review_status="accepted",
                compatibility_category="directly comparable",
            )
        ]
    )

    issues = validate_source_register(register)

    assert any(issue.code == "unverified_source_accepted" for issue in issues)


def test_review_counts_sources_without_misreading_register_as_observations(tmp_path):
    raw = tmp_path / "data" / "raw" / "literature"
    raw.mkdir(parents=True)
    register_path = raw / "source_register.csv"
    observations_path = raw / "literature_observations.csv"
    shutil.copy(LITERATURE / "source_register.csv", register_path)
    shutil.copy(LITERATURE / "literature_observations.csv", observations_path)
    original_register = register_path.read_bytes()
    original_observations = observations_path.read_bytes()

    result = review_literature(tmp_path)

    assert result.sources_discovered == 11
    assert result.sources_verified == 11
    assert result.verification_counts == {
        "abstract_inspected": 1,
        "full_text_inspected": 2,
        "metadata_verified": 8,
        "unverified": 0,
    }
    assert result.sources_reviewed == 2
    assert result.sources_accepted == 0
    assert result.sources_conditional == 1
    assert result.sources_context_only == 9
    assert result.sources_rejected == 2
    assert result.observation_count > 0
    assert result.provenance_complete_observations == 25
    assert not result.errors
    assert result.duplicate_measurement_ids == 0
    assert result.duplicate_observation_rows == 0
    assert all(count == 0 for count in result.compatible_observations_by_target.values())
    assert all(not item["eligible"] for item in result.readiness.values())
    assert any("no accepted directly comparable" in gap for gap in result.data_gaps)
    assert register_path.read_bytes() == original_register
    assert observations_path.read_bytes() == original_observations


def test_literature_cli_writes_report_without_mutating_raw_files(tmp_path):
    raw = tmp_path / "data" / "raw" / "literature"
    raw.mkdir(parents=True)
    shutil.copy(LITERATURE / "source_register.csv", raw / "source_register.csv")
    shutil.copy(
        LITERATURE / "literature_observations.csv",
        raw / "literature_observations.csv",
    )
    register_before = (raw / "source_register.csv").read_bytes()
    observations_before = (raw / "literature_observations.csv").read_bytes()
    reports = tmp_path / "processed" / "literature-review"

    exit_code = main(
        [
            "literature",
            "review",
            "--project-root",
            str(tmp_path),
            "--output-dir",
            str(reports),
        ]
    )

    assert exit_code == 0
    report_json = json.loads(
        (reports / "literature_review.json").read_text(encoding="utf-8")
    )
    assert report_json["sources_verified"] == 11
    assert report_json["sources_discovered"] == 11
    assert report_json["observation_count"] > 0
    assert (raw / "source_register.csv").read_bytes() == register_before
    assert (raw / "literature_observations.csv").read_bytes() == observations_before


def test_unaccepted_source_observations_never_count_as_compatible_or_model_input(tmp_path):
    raw = tmp_path / "data" / "raw" / "literature"
    raw.mkdir(parents=True)
    source = synthetic_source(
        verification_status="metadata_verified",
        review_status="rejected",
        compatibility_category="directly comparable",
        doi="10.1234/unit.test",
        url="https://doi.org/10.1234/unit.test",
        fibre_type="Ipomoea carnea",
        matrix_type="epoxy",
        test_standards="ARTIFICIAL-TEST-STANDARD",
    )
    pd.DataFrame([source]).to_csv(raw / "source_register.csv", index=False)
    obs = {
        "record_id": "UNITTEST-OBSERVATION-001",
        "source_type": "literature",
        "source_id": source["source_id"],
        "publication_title": source["title"],
        "doi_or_url": source["url"],
        "fibre_type": source["fibre_type"],
        "matrix_type": source["matrix_type"],
        "treatment_method": "software test only",
        "naoh_concentration_pct": "",
        "treatment_time_h": "",
        "fibre_loading_wt_pct": "30",
        "fibre_length_mm": "",
        "fibre_form": "test material",
        "fabrication_method": "test method",
        "test_type": "tensile_strength",
        "test_standard": source["test_standards"],
        "measured_value": "10",
        "measured_unit": "MPa",
        "specimen_id": "",
        "batch_id": "",
        "notes": "Isolated automated workflow fixture; not a scientific observation.",
        "review_status": "accepted",
        "compatibility_category": "directly comparable",
        "extraction_type": "reported_mean",
        "source_locator": "",
    }
    pd.DataFrame([obs]).to_csv(raw / "literature_observations.csv", index=False)

    result = review_literature(tmp_path)
    assert result.compatible_observations_by_target["tensile_strength"] == 0
    assert not result.readiness["tensile_strength"]["eligible"]

    # Even a row marked as directly comparable cannot be used unless its source
    # is explicitly accepted in the register. This temp dataset is test-only.
    source["review_status"] = "pending"
    pd.DataFrame([source]).to_csv(raw / "source_register.csv", index=False)
    model_result = run_baseline(
        "tensile_strength",
        project_root=tmp_path,
        output_dir=tmp_path / "reports",
        model_dir=tmp_path / "models",
    )
    assert not model_result.trained
    assert model_result.eligible_record_count == 0
    assert not model_result.metrics
    assert not (tmp_path / "models").exists()


def test_missing_numeric_observation_does_not_count_as_eligible(tmp_path):
    raw = tmp_path / "data" / "raw" / "literature"
    raw.mkdir(parents=True)
    source = synthetic_source(
        verification_status="metadata_verified",
        review_status="accepted",
        compatibility_category="directly comparable",
        doi="10.1234/unit.test",
        fibre_type="Ipomoea carnea",
        matrix_type="epoxy",
    )
    pd.DataFrame([source]).to_csv(raw / "source_register.csv", index=False)
    observations_path = raw / "literature_observations.csv"
    observations_path.write_text(
        "record_id,source_type,source_id,publication_title,doi_or_url,fibre_type,matrix_type,"
        "test_type,test_standard,measured_value,measured_unit,review_status,"
        "compatibility_category\n"
        "UNITTEST-OBS-1,literature,UNITTEST-SOURCE-001,Software-only synthetic source record,"
        "https://doi.org/10.1234/unit.test,Ipomoea carnea,epoxy,tensile_strength,"
        "ARTIFICIAL-TEST-STANDARD,,MPa,accepted,directly comparable\n",
        encoding="utf-8",
    )

    report = review_literature(tmp_path)

    assert report.observation_count == 1
    assert report.compatible_observations_by_target["tensile_strength"] == 0
    assert not report.readiness["tensile_strength"]["eligible"]


def test_duplicate_measurements_are_reported_and_not_model_ready(tmp_path):
    raw = tmp_path / "data" / "raw" / "literature"
    raw.mkdir(parents=True)
    source = synthetic_source(
        verification_status="metadata_verified",
        review_status="accepted",
        compatibility_category="directly comparable",
        doi="10.1234/unit.test",
        fibre_type="Ipomoea carnea",
        matrix_type="epoxy",
    )
    pd.DataFrame([source]).to_csv(raw / "source_register.csv", index=False)
    observation = {
        "record_id": "UNITTEST-DUPLICATE-OBS",
        "source_type": "literature",
        "source_id": source["source_id"],
        "publication_title": source["title"],
        "doi_or_url": "https://doi.org/10.1234/unit.test",
        "fibre_type": "Ipomoea carnea",
        "matrix_type": "epoxy",
        "treatment_method": "",
        "naoh_concentration_pct": "",
        "treatment_time_h": "",
        "fibre_loading_wt_pct": "",
        "fibre_length_mm": "",
        "fibre_form": "",
        "fabrication_method": "",
        "test_type": "tensile_strength",
        "test_standard": "TEST-ONLY-STANDARD",
        "measured_value": "10",
        "measured_unit": "MPa",
        "specimen_id": "",
        "batch_id": "",
        "notes": "Test-only duplicate record.",
        "review_status": "accepted",
        "compatibility_category": "directly comparable",
        "extraction_type": "reported_mean",
        "source_locator": "test fixture only",
    }
    pd.DataFrame([observation, observation]).to_csv(
        raw / "literature_observations.csv", index=False
    )

    report = review_literature(tmp_path)

    assert report.duplicate_measurement_ids == 2
    assert report.duplicate_observation_rows == 2
    assert report.compatible_observations_by_target["tensile_strength"] == 0


def test_audit_counts_register_entries_separately_from_observation_csvs():
    from ecofiber_ai.audit import audit_datasets

    result = audit_datasets(PROJECT)

    assert result.literature_source_register_entries == 11
    assert all(Path(item.path).name != "source_register.csv" for item in result.files)
    assert result.raw_literature_csv_count == 1


def test_integrated_bundle_rows_keep_sources_evidence_and_conflicts_distinct():
    register = pd.read_csv(LITERATURE / "source_register.csv", dtype="string").fillna("")
    observations = pd.read_csv(
        LITERATURE / "literature_observations.csv", dtype="string"
    ).fillna("")
    registered = register.set_index("source_id")

    assert observations["record_id"].is_unique
    assert set(observations["source_id"]) == {
        "WH-EPOXY-SULARDJAKA-2023",
        "BAMBOO-EPOXY-RAMARAO-2018",
    }
    assert registered.loc[
        "WH-EPOXY-SULARDJAKA-2023", "verification_status"
    ] == "full_text_inspected"
    for _, row in observations.iterrows():
        source = registered.loc[row["source_id"]]
        assert row["publication_title"] == source["title"]
        assert row["doi_or_url"] == f"https://doi.org/{source['doi']}"
        assert row["source_locator"]
        assert row["review_status"] in {"pending", "rejected"}
        assert row["compatibility_category"] == "context only"

    by_id = observations.set_index("record_id")
    water_rows = observations.loc[
        observations["source_id"] == "WH-EPOXY-SULARDJAKA-2023"
    ]
    assert water_rows["record_id"].is_unique
    assert water_rows["source_locator"].str.contains(
        "Zenodo record 7746959", regex=False
    ).all()
    assert set(
        water_rows.loc[water_rows["fibre_loading_wt_pct"] != "0", "fibre_type"]
    ) == {
        "Water hyacinth (Eichhornia crassipes)"
    }
    text_values = {
        "WH-EPOXY-SULARDJAKA-2023-WH001": "41",
        "WH-EPOXY-SULARDJAKA-2023-WH002": "45",
        "WH-EPOXY-SULARDJAKA-2023-WH003": "55",
        "WH-EPOXY-SULARDJAKA-2023-WH004": "58",
        "WH-EPOXY-SULARDJAKA-2023-WH005": "59",
        "WH-EPOXY-SULARDJAKA-2023-WH006": "61",
    }
    for record_id, value in text_values.items():
        assert by_id.loc[record_id, "measured_value"] == value
        assert by_id.loc[record_id, "extraction_type"] == "reported_value"
    assert by_id.loc[
        "WH-EPOXY-SULARDJAKA-2023-WHC01-TEXT", "measured_value"
    ] == "67"
    assert by_id.loc[
        "WH-EPOXY-SULARDJAKA-2023-WHC01-FIG", "measured_value"
    ] == "54"
    assert by_id.loc[
        "WH-EPOXY-SULARDJAKA-2023-WHC01-TEXT", "extraction_type"
    ] == "reported_value"
    assert by_id.loc[
        "WH-EPOXY-SULARDJAKA-2023-WHC01-FIG", "extraction_type"
    ] == "graph_estimate"
    assert "Conflict WHC01" in by_id.loc[
        "WH-EPOXY-SULARDJAKA-2023-WHC01-TEXT", "notes"
    ]
    assert {
        "WH-EPOXY-SULARDJAKA-2023-WHC02-TEXT": "51",
        "WH-EPOXY-SULARDJAKA-2023-WHC02-FIG": "59",
        "WH-EPOXY-SULARDJAKA-2023-WHC03-TEXT": "35",
        "WH-EPOXY-SULARDJAKA-2023-WHC03-FIG": "42",
    } == {
        record_id: by_id.loc[record_id, "measured_value"]
        for record_id in [
            "WH-EPOXY-SULARDJAKA-2023-WHC02-TEXT",
            "WH-EPOXY-SULARDJAKA-2023-WHC02-FIG",
            "WH-EPOXY-SULARDJAKA-2023-WHC03-TEXT",
            "WH-EPOXY-SULARDJAKA-2023-WHC03-FIG",
        ]
    }
    assert set(
        observations.loc[
            observations["source_id"] == "BAMBOO-EPOXY-RAMARAO-2018",
            "fibre_type",
        ]
    ) == {"Bamboo (species not stated)"}
    assert not any(
        "Ipomoea carnea" in item
        for item in observations.loc[
            observations["source_id"] == "BAMBOO-EPOXY-RAMARAO-2018",
            "fibre_type",
        ]
    )


@pytest.mark.parametrize(
    "evidence_type",
    ["graph_estimate", "inferred", "reported_value"],
)
def test_evidence_only_values_cannot_train(tmp_path, evidence_type):
    raw = tmp_path / "data" / "raw" / "literature"
    raw.mkdir(parents=True)
    source = synthetic_source(
        verification_status="metadata_verified",
        review_status="accepted",
        compatibility_category="directly comparable",
        doi="10.1234/unit.test",
        url="https://doi.org/10.1234/unit.test",
        fibre_type="test fibre",
        matrix_type="test matrix",
        test_standards="ASTM D3039",
    )
    pd.DataFrame([source]).to_csv(raw / "source_register.csv", index=False)
    observation = {
        "record_id": "UNITTEST-GRAPH-OBSERVATION-001",
        "source_type": "literature",
        "source_id": source["source_id"],
        "publication_title": source["title"],
        "doi_or_url": source["url"],
        "fibre_type": source["fibre_type"],
        "matrix_type": source["matrix_type"],
        "test_type": "tensile_strength",
        "test_standard": source["test_standards"],
        "measured_value": "10",
        "measured_unit": "MPa",
        "review_status": "accepted",
        "compatibility_category": "directly comparable",
        "extraction_type": evidence_type,
        "source_locator": "software-only test row",
    }
    pd.DataFrame([observation]).to_csv(
        raw / "literature_observations.csv", index=False
    )

    review = review_literature(tmp_path)
    result = run_baseline(
        "tensile_strength",
        project_root=tmp_path,
        output_dir=tmp_path / "reports",
        model_dir=tmp_path / "models",
    )

    assert review.observation_count == 1
    assert review.compatible_observations_by_target["tensile_strength"] == 0
    assert not review.readiness["tensile_strength"]["eligible"]
    assert evidence_type not in MODEL_ELIGIBLE_EXTRACTION_TYPES
    assert not result.trained
    assert result.eligible_record_count == 0
    assert result.excluded_reasons[
        "literature evidence type is not eligible for training"
    ] == 1
    assert not result.metrics

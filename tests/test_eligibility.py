"""Tests for evidence eligibility audit and gap analysis."""

import json
from pathlib import Path

import pytest

from ecofiber_ai.__main__ import main
from ecofiber_ai.eligibility import build_eligibility_audit

PROJECT = Path(__file__).parents[1]


def test_eligibility_audit_matches_verified_baseline():
    report = build_eligibility_audit(PROJECT)

    assert report.total_registered_sources == 11
    assert report.total_normalized_observations == 25
    assert report.total_accepted_compatible_observations == 0
    assert report.unready_target_count == 4

    for target in ("tensile_strength", "flexural_strength", "impact_resistance", "water_absorption"):
        summary = report.targets[target]
        assert not summary.model_ready
        assert summary.accepted_compatible_observations == 0
        assert len(summary.reasons_not_ready) > 0
        assert len(summary.evidence_needed_for_readiness) > 0

    assert len(report.observation_records) == 25
    for obs in report.observation_records:
        assert not obs.is_eligible
        assert len(obs.reasons_ineligible) > 0


def test_eligibility_cli_writes_markdown_and_json(tmp_path):
    output_dir = tmp_path / "processed"

    exit_code = main(["eligibility", "--project-root", str(PROJECT), "--output-dir", str(output_dir)])

    assert exit_code == 0
    md_file = output_dir / "eligibility_audit.md"
    json_file = output_dir / "eligibility_audit.json"

    assert md_file.is_file()
    assert json_file.is_file()

    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert data["total_registered_sources"] == 11
    assert data["total_normalized_observations"] == 25
    assert data["total_accepted_compatible_observations"] == 0
    assert data["unready_target_count"] == 4

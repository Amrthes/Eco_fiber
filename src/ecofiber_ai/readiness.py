"""End-to-end, non-training readiness report for the EcoFiber AI demo."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ecofiber_ai.audit import (
    MINIMUM_INDEPENDENT_GROUPS,
    MINIMUM_MODEL_RECORDS,
    DatasetAudit,
    FileAudit,
    audit_datasets,
)
from ecofiber_ai.experimental import (
    ExperimentalQualityReport,
    review_experimental_csv,
)
from ecofiber_ai.literature import LiteratureReview, review_literature
from ecofiber_ai.modeling import MINIMUM_TEST_RECORDS, MINIMUM_TRAIN_RECORDS
from ecofiber_ai.schema import TEST_TYPES, canonical_unit
from ecofiber_ai.validation import CSVLoadError, load_csv


@dataclass
class ReadinessReport:
    """Traceable snapshot of data availability without fitting a model."""

    project_root: str
    audit_report: str
    literature_report: str
    experimental_reports: list[str]
    experimental_files: list[dict[str, Any]]
    literature_summary: dict[str, Any]
    targets: dict[str, dict[str, Any]]
    training_gates: dict[str, int]
    demo_status: str
    model_training_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [
            "# EcoFiber AI end-to-end readiness",
            "",
            f"- Project root: `{self.project_root}`",
            "- This command performs readiness checks only; no model was trained "
            "and no prediction was generated.",
            f"- Demo status: **{self.demo_status}**",
            f"- Dataset audit: `{self.audit_report}`",
            f"- Literature review: `{self.literature_report}`",
            "",
            "## Experimental data",
            "",
        ]
        if not self.experimental_files:
            lines.extend(
                [
                    "No raw experimental observation CSVs were found. The "
                    "header-only template is not a dataset.",
                    "Accepted: 0; requires review: 0; rejected: 0.",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "| File | Rows | Accepted | Review | Rejected |",
                    "|---|---:|---:|---:|---:|",
                ]
            )
            for item in self.experimental_files:
                lines.append(
                    f"| `{item['path']}` | {item['record_count']} | "
                    f"{item['accepted_count']} | {item['review_count']} | "
                    f"{item['rejected_count']} |"
                )
            lines.append("")
            lines.extend(["### Experimental file review details", ""])
            for item in self.experimental_files:
                lines.append(f"- `{item['path']}`")
                if item.get("error"):
                    lines.append(f"  - Review error: {item['error']}")
                for target, readiness in item.get("target_readiness", {}).items():
                    missing = ", ".join(
                        f"{field}: {count}"
                        for field, count in readiness["missing_metadata_counts"].items()
                        if count
                    ) or "none"
                    lines.append(
                        f"  - `{target}`: {readiness['observation_count']} rows; "
                        f"{readiness['accepted_observation_count']} accepted; "
                        f"{readiness['unique_specimen_count']} specimen IDs; "
                        f"{readiness['independent_group_count']} batch IDs; "
                        f"units {', '.join(readiness['units']) or 'none'}; "
                        f"missing metadata: {missing}; {readiness['status']}."
                    )
            lines.append("")

        lit = self.literature_summary
        lines.extend(
            [
                "## Literature evidence",
                "",
                f"- Registered sources: {lit['sources_discovered']}",
                f"- Metadata-verified: {lit['metadata_verified']}",
                f"- Abstract inspected: {lit['abstract_inspected']}",
                f"- Full text inspected: {lit['full_text_inspected']}",
                f"- Extracted observations: {lit['observation_count']}",
                f"- Provenance-complete observations: {lit['provenance_complete_observations']}",
                f"- Accepted sources: {lit['sources_accepted']}",
                "",
                "## Target readiness",
                "",
                "| Target | Experimental rows / accepted | Unique specimen IDs by file | Batch groups by file | Units by file | Literature rows / accepted compatible | Independent literature groups | Status |",
                "|---|---:|---|---|---|---:|---:|---|",
            ]
        )
        for target in sorted(TEST_TYPES):
            item = self.targets[target]
            exp_rows = item["experimental"]
            exp_value = (
                f"{exp_rows['observation_count']} / "
                f"{exp_rows['accepted_observation_count']}"
            )
            specimens = ", ".join(
                f"`{path}`: {count}"
                for path, count in exp_rows["unique_specimen_counts_by_file"].items()
            ) or "none"
            batches = ", ".join(
                f"`{path}`: {count}"
                for path, count in exp_rows["batch_groups_by_file"].items()
            ) or "none"
            units = ", ".join(
                f"`{path}`: {', '.join(values) or 'none'}"
                for path, values in exp_rows["units_by_file"].items()
            ) or "none"
            lit_value = (
                f"{item['literature']['observation_count']} / "
                f"{item['literature']['accepted_compatible_count']}"
            )
            status = "not ready" if not item["model_request_candidate"] else (
                "candidate; explicit model review still required"
            )
            lines.append(
                f"| `{target}` | {exp_value} | {specimens} | {batches} | {units} "
                f"| {lit_value} | {item['literature']['independent_groups']} "
                f"| {status} |"
            )
        lines.extend(["", "### Readiness reasons", ""])
        for target in sorted(TEST_TYPES):
            item = self.targets[target]
            reasons = item["reasons"] or [
                "Existing data/readiness checks passed; the model command has not been run."
            ]
            lines.append(f"- `{target}`: " + "; ".join(reasons))
        lines.extend(
            [
                "",
                "## Interpretation and next steps",
                "",
                "Experimental files and literature observations are assessed "
                "separately; this report does not pool them. Separate raw files "
                "are not combined to meet the model thresholds. A candidate "
                "status is not a trained model or scientific validation.",
                "",
                "For each desired target, enter real specimen-level measurements "
                "with traceable source, fibre/matrix/treatment/loading, fabrication "
                "and test-standard metadata; validate and review them; and meet "
                "the unchanged gates below. A single raw CSV is evaluated at a "
                "time; separate sources are not pooled by this demo.",
                "",
                "Current model gates: "
                f"{self.training_gates['minimum_compatible_observations']} compatible "
                f"observations; {self.training_gates['minimum_independent_groups']} "
                f"independent source/batch groups; at least "
                f"{self.training_gates['minimum_train_records']} training and "
                f"{self.training_gates['minimum_test_records']} holdout observations.",
                "",
                "No illustrative values are used in this report.",
                "",
            ]
        )
        return "\n".join(lines)

    def write(self, directory: str | Path) -> tuple[Path, Path]:
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        markdown = destination / "readiness_report.md"
        json_path = destination / "readiness_report.json"
        markdown.write_text(self.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return markdown, json_path


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _metadata_counts(literature: LiteratureReview) -> dict[str, Any]:
    counts = literature.verification_counts
    return {
        "sources_discovered": literature.sources_discovered,
        "metadata_verified": counts.get("metadata_verified", 0),
        "abstract_inspected": counts.get("abstract_inspected", 0),
        "full_text_inspected": counts.get("full_text_inspected", 0),
        "sources_accepted": literature.sources_accepted,
        "observation_count": literature.observation_count,
        "provenance_complete_observations": literature.provenance_complete_observations,
    }


def build_readiness_report(project_root: str | Path = ".") -> ReadinessReport:
    """Refresh linked reports and summarize real-data readiness; never trains."""
    root = Path(project_root).resolve()
    processed = root / "data" / "processed"
    audit: DatasetAudit = audit_datasets(root)
    audit_path = audit.write_markdown(processed / "dataset_audit.md")

    literature = review_literature(root)
    literature_dir = processed / "literature-review"
    literature_markdown, _ = literature.write(literature_dir)

    experimental_audits = [
        item for item in audit.files if item.area == "raw_experimental"
    ]
    experimental_files: list[dict[str, Any]] = []
    experimental_reports: list[str] = []
    experimental_by_target: dict[str, list[tuple[FileAudit, ExperimentalQualityReport]]] = {
        target: [] for target in TEST_TYPES
    }
    if experimental_audits:
        for file_audit in experimental_audits:
            source = root / Path(file_audit.path)
            try:
                quality = review_experimental_csv(source)
            except CSVLoadError as exc:
                experimental_files.append(
                    {
                        "path": file_audit.path,
                        "record_count": file_audit.record_count,
                        "accepted_count": 0,
                        "review_count": 0,
                        "rejected_count": 0,
                        "test_fixture_marked": file_audit.test_fixture_marked,
                        "error": str(exc),
                        "target_readiness": {},
                    }
                )
                continue
            report_dir = (
                processed
                / "experimental-review"
                / Path(file_audit.path).with_suffix("").name
            )
            markdown_path, _ = quality.write(report_dir)
            experimental_reports.append(_relative(markdown_path, root))
            experimental_files.append(
                {
                    "path": file_audit.path,
                    "record_count": quality.record_count,
                    "accepted_count": quality.accepted_count,
                    "review_count": quality.review_count,
                    "rejected_count": quality.rejected_count,
                    "test_fixture_marked": file_audit.test_fixture_marked,
                    "target_readiness": quality.target_readiness,
                }
            )
            for target in TEST_TYPES:
                experimental_by_target[target].append((file_audit, quality))
    else:
        template = root / "data" / "templates" / "experimental_observations_template.csv"
        if template.is_file():
            quality = review_experimental_csv(template)
            markdown_path, _ = quality.write(processed / "experimental-review")
            experimental_reports.append(_relative(markdown_path, root))

    literature_observations_path = (
        root / "data" / "raw" / "literature" / "literature_observations.csv"
    )
    literature_observations = pd.DataFrame()
    literature_observation_error: str | None = None
    if literature_observations_path.is_file():
        try:
            literature_observations = load_csv(literature_observations_path)
        except CSVLoadError as exc:
            literature_observation_error = str(exc)

    target_summaries: dict[str, dict[str, Any]] = {}
    for target in sorted(TEST_TYPES):
        row_count = accepted_count = 0
        specimen_counts: dict[str, int] = {}
        batch_counts: dict[str, int] = {}
        units_by_file: dict[str, list[str]] = {}
        experimental_reasons: list[str] = []
        experimental_candidate = False
        for file_audit, quality in experimental_by_target[target]:
            item = quality.target_readiness[target]
            file_path = file_audit.path
            row_count += item["observation_count"]
            accepted_count += item["accepted_observation_count"]
            specimen_counts[file_path] = item["unique_specimen_count"]
            batch_counts[file_path] = item["independent_group_count"]
            units_by_file[file_path] = item["units"]
            if not file_audit.modelling_readiness.get(target, {}).get("eligible", False):
                experimental_reasons.extend(
                    file_audit.modelling_readiness.get(target, {}).get(
                        "reasons", ["existing audit did not consider the file eligible"]
                    )
                )
            if item["status"] != "potentially ready":
                experimental_reasons.extend(item["reasons"])
            if (
                item["status"] == "potentially ready"
                and file_audit.modelling_readiness.get(target, {}).get("eligible", False)
                and not file_audit.test_fixture_marked
            ):
                experimental_candidate = True

        lit_ready = literature.readiness[target]
        lit_units: list[str] = []
        target_observation_count = 0
        if {"test_type", "measured_unit"}.issubset(literature_observations.columns):
            lit_target = literature_observations.loc[
                literature_observations["test_type"].astype(str).str.strip().eq(target)
            ]
            target_observation_count = len(lit_target)
            lit_units = sorted(
                {
                    canonical_unit(str(value).strip()) or str(value).strip()
                    for value in lit_target["measured_unit"].tolist()
                    if str(value).strip()
                }
            )
        literature_candidate = bool(lit_ready["eligible"])
        reasons = list(dict.fromkeys(experimental_reasons))
        reasons.extend(
            f"literature: {reason}" for reason in lit_ready["reasons"]
        )
        if not experimental_by_target[target] and row_count == 0:
            reasons[:0] = [
                "no raw experimental observations are available",
                f"experimental modelling requires at least {MINIMUM_MODEL_RECORDS} "
                "compatible observations and "
                f"{MINIMUM_INDEPENDENT_GROUPS} independent source/batch groups",
            ]
        if literature.observation_count == 0:
            reasons.append("literature observation table contains no extracted measurements")
        if literature_observation_error:
            reasons.append(
                "literature observation table could not be read: "
                + literature_observation_error
            )
        target_summaries[target] = {
            "experimental": {
                "observation_count": row_count,
                "accepted_observation_count": accepted_count,
                "unique_specimen_counts_by_file": specimen_counts,
                "batch_groups_by_file": batch_counts,
                "units_by_file": units_by_file,
            },
            "literature": {
                "observation_count": target_observation_count,
                "accepted_compatible_count": literature.compatible_observations_by_target.get(
                    target, 0
                ),
                "independent_groups": lit_ready["independent_groups"],
                "units": lit_units,
            },
            "model_request_candidate": experimental_candidate or literature_candidate,
            "reasons": list(dict.fromkeys(reasons)),
        }

    status = (
        "Readiness report generated; no target is ready for a model request."
        if not any(item["model_request_candidate"] for item in target_summaries.values())
        else "Some target(s) meet current data checks; no model was run."
    )
    return ReadinessReport(
        project_root=str(root),
        audit_report=_relative(audit_path, root),
        literature_report=_relative(literature_markdown, root),
        experimental_reports=experimental_reports,
        experimental_files=experimental_files,
        literature_summary=_metadata_counts(literature),
        targets=target_summaries,
        training_gates={
            "minimum_compatible_observations": MINIMUM_MODEL_RECORDS,
            "minimum_independent_groups": MINIMUM_INDEPENDENT_GROUPS,
            "minimum_train_records": MINIMUM_TRAIN_RECORDS,
            "minimum_test_records": MINIMUM_TEST_RECORDS,
        },
        demo_status=status,
    )

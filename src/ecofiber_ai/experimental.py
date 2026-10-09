"""Quality review for experimental observation CSVs."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ecofiber_ai.audit import (
    MINIMUM_INDEPENDENT_GROUPS,
    MINIMUM_MODEL_RECORDS,
    is_test_fixture,
)
from ecofiber_ai.schema import CANONICAL_COLUMNS, TEST_TYPES, canonical_unit
from ecofiber_ai.validation import CSVLoadError, load_csv, validate_dataframe

EXPERIMENTAL_METADATA_COLUMNS = (
    "replicate_id",
    "resin_hardener_ratio",
    "curing_temperature_c",
    "curing_time_h",
    "measurement_date",
    "measurement_source",
)
REVIEW_FIELDS = (
    "specimen_id",
    "batch_id",
    "fibre_type",
    "matrix_type",
    "treatment_method",
    "naoh_concentration_pct",
    "fibre_loading_wt_pct",
    "fabrication_method",
    "test_standard",
    "measurement_date",
    "measurement_source",
)


@dataclass(frozen=True)
class RecordDecision:
    """Quality status and reasons for one original row."""

    record_id: str
    specimen_id: str
    test_type: str
    status: str
    reasons: tuple[str, ...]


@dataclass
class ExperimentalQualityReport:
    """Data quality counts and per-target readiness for an input file."""

    source_file: str
    record_count: int
    accepted_count: int
    review_count: int
    rejected_count: int
    decisions: list[RecordDecision]
    target_readiness: dict[str, dict[str, Any]]
    dataset_unit_consistency: dict[str, list[str]]
    raw_file_preserved: bool

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["decisions"] = [asdict(decision) for decision in self.decisions]
        return result

    def to_markdown(self) -> str:
        lines = [
            "# Experimental data quality review",
            "",
            f"- Input: `{self.source_file}`",
            f"- Records: {self.record_count}",
            f"- Accepted: {self.accepted_count}",
            f"- Requires review: {self.review_count}",
            f"- Rejected: {self.rejected_count}",
            f"- Raw input preserved: {'yes' if self.raw_file_preserved else 'no'}",
            "",
            "## Target readiness",
            "",
            "| Target | Observations | Accepted | Unique specimens | Independent batches/groups | Units | Status | Reasons |",
            "|---|---:|---:|---:|---:|---|---|---|",
        ]
        for target in sorted(TEST_TYPES):
            item = self.target_readiness[target]
            lines.append(
                f"| `{target}` | {item['observation_count']} | "
                f"{item['accepted_observation_count']} | "
                f"{item['unique_specimen_count']} | {item['independent_group_count']} | "
                f"{', '.join(item['units']) or 'none'} | {item['status']} | "
                f"{'; '.join(item['reasons']) or 'none'} |"
            )
        lines.extend(["", "## Record decisions", ""])
        if not self.decisions:
            lines.append("No observation records were supplied.")
        for decision in self.decisions:
            detail = "; ".join(decision.reasons) or "no review findings"
            lines.append(
                f"- `{decision.record_id or '(missing record_id)'}` "
                f"(specimen `{decision.specimen_id or '(missing)'}`, "
                f"{decision.test_type or 'unknown property'}): "
                f"**{decision.status}** — {detail}"
            )
        return "\n".join(lines) + "\n"

    def write(self, directory: str | Path) -> tuple[Path, Path]:
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        markdown_path = destination / "experimental_quality_review.md"
        json_path = destination / "experimental_quality_review.json"
        markdown_path.write_text(self.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return markdown_path, json_path


def _present(value: Any) -> bool:
    return not pd.isna(value) and bool(str(value).strip())


def _text(value: Any) -> str:
    return "" if not _present(value) else str(value).strip()


def _build_target_readiness(
    frame: pd.DataFrame,
    decisions: list[RecordDecision],
    target: str,
) -> dict[str, Any]:
    selected = frame.loc[
        frame.get("test_type", pd.Series(index=frame.index, dtype="string"))
        .astype(str)
        .str.strip()
        .eq(target)
    ]
    if "source_type" in selected.columns:
        selected = selected.loc[
            selected["source_type"].astype(str).str.strip().eq("experimental")
        ]
    accepted_ids = {
        decision.record_id
        for decision in decisions
        if decision.status == "accepted"
    }
    target_ids = selected.get("record_id", pd.Series(index=selected.index, dtype="string"))
    accepted = selected.loc[target_ids.astype(str).isin(accepted_ids)]
    specimens = {
        _text(value) for value in selected.get("specimen_id", [])
        if _present(value)
    }
    batches = {
        _text(value) for value in selected.get("batch_id", [])
        if _present(value)
    }
    accepted_batches = {
        _text(value) for value in accepted.get("batch_id", [])
        if _present(value)
    }
    units = sorted(
        {
            canonical_unit(_text(value)) or _text(value)
            for value in selected.get("measured_unit", [])
            if _present(value)
        }
    )
    missing = {
        field: int(sum(not _present(value) for value in selected.get(field, [])))
        for field in REVIEW_FIELDS
    }
    reasons: list[str] = []
    if accepted.empty:
        reasons.append("no accepted real observations for this target")
    if len(accepted) < MINIMUM_MODEL_RECORDS:
        reasons.append(
            f"fewer than {MINIMUM_MODEL_RECORDS} accepted observations ({len(accepted)})"
        )
    if len(accepted_batches) < MINIMUM_INDEPENDENT_GROUPS:
        reasons.append(
            f"fewer than {MINIMUM_INDEPENDENT_GROUPS} independent accepted batch groups "
            f"({len(accepted_batches)})"
        )
    if selected.shape[0] and len(units) != 1:
        reasons.append("accepted target observations do not have one consistent unit")
    if any(missing[field] for field in ("test_standard", "fabrication_method")):
        reasons.append("test standard or fabrication metadata is missing")
    return {
        "observation_count": len(selected),
        "accepted_observation_count": len(accepted),
        "unique_specimen_count": len(specimens),
        "independent_group_count": len(batches),
        "accepted_independent_group_count": len(accepted_batches),
        "units": units,
        "missing_metadata_counts": missing,
        "status": "potentially ready" if not reasons else "not ready",
        "reasons": reasons,
    }


def review_experimental_csv(path: str | Path) -> ExperimentalQualityReport:
    """Review input records without modifying, dropping, or rewriting the CSV."""
    source = Path(path)
    try:
        frame = load_csv(source)
    except CSVLoadError:
        raise

    validation = validate_dataframe(frame)
    fixture = is_test_fixture(frame, source)
    reasons_by_row: dict[int, list[str]] = defaultdict(list)
    rejected_rows: set[int] = set()
    id_to_rows: dict[str, list[int]] = defaultdict(list)
    for index, row in frame.iterrows():
        record_id = _text(row.get("record_id", ""))
        if record_id:
            id_to_rows[record_id].append(index)

    for issue in validation.errors:
        if issue.record_id is not None:
            for index in id_to_rows.get(issue.record_id, []):
                reasons_by_row[index].append(f"{issue.code}: {issue.message}")
                rejected_rows.add(index)
        elif not frame.empty:
            for index in frame.index:
                reasons_by_row[index].append(f"{issue.code}: {issue.message}")
                rejected_rows.add(index)

    if "source_type" in frame.columns:
        wrong_source_rows = frame.index[
            frame["source_type"].astype(str).str.strip().ne("experimental")
        ]
        for index in wrong_source_rows:
            reasons_by_row[index].append(
                "experimental review accepts only source_type='experimental'"
            )
            rejected_rows.add(index)

    for record_id, indices in id_to_rows.items():
        if len(indices) > 1:
            for index in indices:
                reasons_by_row[index].append(
                    f"duplicate record_id '{record_id}' appears more than once"
                )
                rejected_rows.add(index)

    if fixture:
        for index in frame.index:
            reasons_by_row[index].append(
                "test/artificial fixture data cannot be reviewed as research data"
            )
            rejected_rows.add(index)

    specimen_test_rows: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for index, row in frame.iterrows():
        specimen_id = _text(row.get("specimen_id", ""))
        test_type = _text(row.get("test_type", ""))
        unit = canonical_unit(_text(row.get("measured_unit", ""))) or _text(
            row.get("measured_unit", "")
        )
        replicate_id = _text(row.get("replicate_id", ""))
        if specimen_id and test_type:
            specimen_test_rows[(specimen_id, test_type, unit, replicate_id)].append(index)

    for key, indices in specimen_test_rows.items():
        if len(indices) < 2:
            continue
        values = {
            pd.to_numeric(
                pd.Series([frame.loc[index].get("measured_value", "")]),
                errors="coerce",
            ).iloc[0]
            for index in indices
        }
        record_ids = [ _text(frame.loc[index].get("record_id", "")) for index in indices ]
        if len(values) == 1:
            label = "duplicate specimen/property/replicate measurement"
            for index in indices:
                reasons_by_row[index].append(label)
                rejected_rows.add(index)
        else:
            label = "conflicting values for the same specimen/property/replicate"
            for index in indices:
                reasons_by_row[index].append(label)

    unit_consistency: dict[str, list[str]] = {}
    if "test_type" in frame.columns and "measured_unit" in frame.columns:
        for target in sorted(TEST_TYPES):
            units = sorted(
                {
                    canonical_unit(_text(value)) or _text(value)
                    for value in frame.loc[
                        frame["test_type"].astype(str).str.strip().eq(target),
                        "measured_unit",
                    ].tolist()
                    if _present(value)
                }
            )
            unit_consistency[target] = units
            if len(units) > 1:
                for index in frame.index[
                    frame["test_type"].astype(str).str.strip().eq(target)
                ]:
                    reasons_by_row[index].append(
                        f"inconsistent units for {target}: {', '.join(units)}"
                    )

    decisions: list[RecordDecision] = []
    for index, row in frame.iterrows():
        for field in ("curing_temperature_c", "curing_time_h"):
            value = _text(row.get(field, ""))
            if value:
                try:
                    parsed = float(value)
                except (TypeError, ValueError, OverflowError):
                    parsed = float("nan")
                invalid = pd.isna(parsed) or parsed in (float("inf"), float("-inf"))
                if field == "curing_time_h" and not pd.isna(parsed) and parsed < 0:
                    invalid = True
                if invalid:
                    reasons_by_row[index].append(
                        f"invalid experimental metadata: {field} must be "
                        + ("finite and non-negative" if field == "curing_time_h" else "finite")
                    )
                    rejected_rows.add(index)
        measurement_date = _text(row.get("measurement_date", ""))
        if measurement_date:
            try:
                if len(measurement_date) != 10:
                    raise ValueError
                pd.to_datetime(measurement_date, format="%Y-%m-%d", errors="raise")
            except (TypeError, ValueError):
                reasons_by_row[index].append(
                    "invalid experimental metadata: measurement_date must use YYYY-MM-DD"
                )
                rejected_rows.add(index)
        row_reasons = list(dict.fromkeys(reasons_by_row[index]))
        for field in REVIEW_FIELDS:
            if not _present(row.get(field, "")):
                row_reasons.append(f"missing review metadata: {field}")
        status = (
            "rejected"
            if index in rejected_rows
            else "review"
            if row_reasons
            else "accepted"
        )
        decisions.append(
            RecordDecision(
                record_id=_text(row.get("record_id", "")),
                specimen_id=_text(row.get("specimen_id", "")),
                test_type=_text(row.get("test_type", "")),
                status=status,
                reasons=tuple(dict.fromkeys(row_reasons)),
            )
        )

    target_readiness = {
        target: _build_target_readiness(frame, decisions, target)
        for target in sorted(TEST_TYPES)
    }
    return ExperimentalQualityReport(
        source_file=str(source),
        record_count=len(frame),
        accepted_count=sum(decision.status == "accepted" for decision in decisions),
        review_count=sum(decision.status == "review" for decision in decisions),
        rejected_count=sum(decision.status == "rejected" for decision in decisions),
        decisions=decisions,
        target_readiness=target_readiness,
        dataset_unit_consistency=unit_consistency,
        raw_file_preserved=True,
    )

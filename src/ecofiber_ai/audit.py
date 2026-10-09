"""Dataset inventory and modelling-readiness audit."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ecofiber_ai.schema import (
    CANONICAL_COLUMNS,
    SUPPORTED_UNITS,
    TEST_TYPES,
    canonical_unit,
)
from ecofiber_ai.validation import CSVLoadError, load_csv, validate_dataframe

MINIMUM_MODEL_RECORDS = 12
MINIMUM_INDEPENDENT_GROUPS = 4
_SUMMARIZED_FIELDS = (
    "source_id",
    "publication_title",
    "doi_or_url",
    "fibre_type",
    "matrix_type",
    "treatment_method",
    "naoh_concentration_pct",
    "fibre_loading_wt_pct",
    "fibre_length_mm",
    "fibre_form",
    "fabrication_method",
    "test_type",
    "measured_unit",
    "test_standard",
    "source_type",
)
_PROVENANCE_FIELDS = ("source_id", "fibre_type", "matrix_type", "test_standard")
_IDENTIFIER_TEST_MARKER = re.compile(
    r"\bartificial\b|\bsynthetic[-_\s](?:fixture|test(?:[-_\s]data)?)\b"
    r"|\btest[\s_-]*fixture\b",
    re.IGNORECASE,
)
_DESCRIPTION_TEST_MARKER = re.compile(
    r"\bartificial[-_\s](?:test[-_\s])?fixture\b"
    r"|\bsynthetic[-_\s]fixture\b|\btest[\s_-]*fixture\b",
    re.IGNORECASE,
)


@dataclass
class FileAudit:
    """Inventory and provenance details for one CSV path."""

    path: str
    area: str
    record_count: int | None
    test_fixture_marked: bool = False
    source_types: list[str] = field(default_factory=list)
    available_values: dict[str, list[str]] = field(default_factory=dict)
    missing_value_counts: dict[str, int] = field(default_factory=dict)
    duplicate_record_ids: int = 0
    duplicate_rows: int = 0
    provenance_complete_records: int = 0
    provenance_incomplete_records: int = 0
    modelling_readiness: dict[str, dict[str, Any]] = field(default_factory=dict)
    error: str | None = None


@dataclass
class DatasetAudit:
    """Whole-project data inventory."""

    project_root: str
    csv_file_count: int
    raw_experimental_csv_count: int
    raw_literature_csv_count: int
    processed_csv_count: int
    literature_source_register_entries: int
    real_dataset_status: str
    files: list[FileAudit]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_json(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return destination

    def to_markdown(self) -> str:
        lines = [
            "# EcoFiber AI dataset audit",
            "",
            f"- Project root: `{self.project_root}`",
            f"- CSV files found: {self.csv_file_count}",
            f"- Raw experimental CSVs: {self.raw_experimental_csv_count}",
            f"- Raw literature CSVs: {self.raw_literature_csv_count}",
            f"- Processed CSVs: {self.processed_csv_count}",
            f"- Bibliographic source-register entries (not measurements): {self.literature_source_register_entries}",
            f"- Real dataset status: **{self.real_dataset_status}**",
            "",
            "No file in `tests/fixtures/` is scanned or considered research data.",
            "Raw experimental and literature inputs are inventoried separately; "
            "this report does not merge them.",
            "",
            "## Files",
            "",
        ]
        if not self.files:
            lines.append("No CSV datasets were found in the configured data directories.")
            return "\n".join(lines) + "\n"

        for item in self.files:
            lines.extend(
                [
                    f"### `{item.path}` ({item.area})",
                    "",
                    f"- Records: {item.record_count if item.record_count is not None else 'unavailable'}",
                    f"- Test/artificial fixture marker: {'yes (excluded from scientific data)' if item.test_fixture_marked else 'no marker detected'}",
                    f"- Source types: {', '.join(item.source_types) if item.source_types else 'missing'}",
                    f"- Duplicate record IDs: {item.duplicate_record_ids}",
                    f"- Duplicate complete rows: {item.duplicate_rows}",
                    f"- Provenance-complete records: {item.provenance_complete_records}",
                    f"- Provenance-incomplete records: {item.provenance_incomplete_records}",
                ]
            )
            if item.error:
                lines.append(f"- Read error: {item.error}")
            if item.available_values:
                lines.extend(["", "Available values:"])
                for name, values in item.available_values.items():
                    lines.append(
                        f"- `{name}`: {', '.join(f'`{value}`' for value in values) or 'missing'}"
                    )
            if item.missing_value_counts:
                lines.extend(["", "Missing values by canonical field:"])
                lines.extend(
                    f"- `{name}`: {count}" for name, count in item.missing_value_counts.items()
                )
            if item.modelling_readiness:
                lines.extend(["", "Target-property modelling readiness:"])
                for target, readiness in item.modelling_readiness.items():
                    status = "potentially eligible" if readiness["eligible"] else "not ready"
                    reasons = "; ".join(readiness["reasons"]) or "meets structural thresholds"
                    lines.append(
                        f"- `{target}`: **{status}** "
                        f"({readiness['compatible_record_count']} compatible records, "
                        f"{readiness['independent_group_count']} independent groups; "
                        f"units: {', '.join(readiness['units']) or 'missing'}) — {reasons}"
                    )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def write_markdown(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.to_markdown(), encoding="utf-8")
        return destination


def _nonblank_values(dataframe: pd.DataFrame, column: str) -> list[str]:
    if column not in dataframe.columns:
        return []
    values = {
        str(value).strip()
        for value in dataframe[column].tolist()
        if not pd.isna(value) and str(value).strip()
    }
    return sorted(values, key=str.casefold)


def is_test_fixture(dataframe: pd.DataFrame, path: str | Path) -> bool:
    """Detect explicit artificial/test fixture markers in path or provenance fields."""
    source = Path(path)
    if any(part.casefold() in {"tests", "fixtures"} for part in source.parts):
        return True
    if _DESCRIPTION_TEST_MARKER.search(source.name):
        return True
    for column in ("record_id", "source_id"):
        if column in dataframe.columns and dataframe[column].astype(str).map(
            lambda value: bool(_IDENTIFIER_TEST_MARKER.search(value))
        ).any():
            return True
    return "notes" in dataframe.columns and dataframe["notes"].astype(str).map(
        lambda value: bool(_DESCRIPTION_TEST_MARKER.search(value))
    ).any()


def _missing_counts(dataframe: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    for column in CANONICAL_COLUMNS:
        if column not in dataframe.columns:
            counts[column] = len(dataframe)
        else:
            counts[column] = int(
                sum(pd.isna(value) for value in dataframe[column].tolist())
                + sum(
                    isinstance(value, str) and not value.strip()
                    for value in dataframe[column].tolist()
                )
            )
    return counts


def _groups_for(frame: pd.DataFrame) -> tuple[str | None, int]:
    if "source_id" not in frame.columns:
        return None, 0
    source = frame["source_id"].astype("string").str.strip()
    if "batch_id" in frame.columns:
        batch = frame["batch_id"].astype("string").str.strip()
        if source.notna().all() and batch.notna().all() and (batch != "").all():
            return "source_id+batch_id", int((source + "::" + batch).nunique())
    if source.notna().all() and (source != "").all():
        return "source_id", int(source.nunique())
    return None, 0


def _target_readiness(dataframe: pd.DataFrame, target: str) -> dict[str, Any]:
    reasons: list[str] = []
    if "test_type" not in dataframe.columns or "measured_value" not in dataframe.columns:
        return {
            "eligible": False,
            "compatible_record_count": 0,
            "independent_group_count": 0,
            "grouping_strategy": None,
            "units": [],
            "reasons": ["target observations or measured_value column are absent"],
        }

    if "test_type" not in dataframe.columns:
        subset = dataframe.iloc[0:0].copy()
    else:
        subset = dataframe[dataframe["test_type"].astype(str).str.strip() == target].copy()
    if subset.empty:
        reasons.append("no observations for this target")

    if "measured_unit" not in subset.columns:
        subset = subset.iloc[0:0]
        reasons.append("measurement units are missing")
    else:
        valid_units = SUPPORTED_UNITS[target]
        unit_ok = pd.Series(
            [
                canonical_unit(str(value)) in valid_units
                if not pd.isna(value)
                else False
                for value in subset["measured_unit"].tolist()
            ],
            index=subset.index,
            dtype=bool,
        )
        numeric = pd.to_numeric(subset["measured_value"], errors="coerce")
        finite = pd.Series(
            [
                pd.notna(value) and math.isfinite(float(value))
                for value in numeric.tolist()
            ],
            index=subset.index,
            dtype=bool,
        )
        subset = subset[unit_ok & finite].copy()
        subset["measured_value"] = pd.to_numeric(subset["measured_value"], errors="coerce")
        reasons.extend(
            ["target has no supported-unit, finite numeric observations"]
            if subset.empty and "no observations for this target" not in reasons
            else []
        )
        target_units = {
            canonical_unit(str(value))
            for value in subset["measured_unit"].tolist()
            if not pd.isna(value)
        }
        if len(target_units) > 1:
            reasons.append(
                "multiple compatible unit scales are present; select one before modelling"
            )

    if not subset.empty:
        for field_name in ("fibre_type", "matrix_type", "test_standard"):
            missing = (
                field_name not in subset.columns
                or any(
                    pd.isna(value) or not str(value).strip()
                    for value in subset[field_name].tolist()
                )
            )
            if missing:
                reasons.append(
                    f"'{field_name}' metadata is missing for compatible target observations"
                )
            elif subset[field_name].nunique() != 1:
                reasons.append(f"'{field_name}' varies; compatibility requires review")

        source_values = (
            subset["source_type"].astype(str).str.strip().tolist()
            if "source_type" in subset.columns
            else []
        )
        if not source_values or any(
            value not in {"experimental", "literature"} for value in source_values
        ):
            reasons.append("valid source_type metadata is missing")
        elif len(set(source_values)) != 1:
            reasons.append("source types are mixed")
        elif source_values[0] == "literature":
            citation_columns = [
                column
                for column in ("publication_title", "doi_or_url")
                if column in subset.columns
            ]
            if not citation_columns or any(
                not any(
                    not pd.isna(row.get(column))
                    and str(row.get(column)).strip()
                    for column in citation_columns
                )
                for _, row in subset.iterrows()
            ):
                reasons.append("literature publication citation metadata is incomplete")

    grouping_strategy, group_count = _groups_for(subset)
    if group_count < MINIMUM_INDEPENDENT_GROUPS:
        reasons.append(
            f"fewer than {MINIMUM_INDEPENDENT_GROUPS} independent source/batch groups"
        )
    if len(subset) < MINIMUM_MODEL_RECORDS:
        reasons.append(
            f"fewer than {MINIMUM_MODEL_RECORDS} compatible observations"
        )
    return {
        "eligible": not reasons,
        "compatible_record_count": len(subset),
        "independent_group_count": group_count,
        "grouping_strategy": grouping_strategy,
        "units": _nonblank_values(subset, "measured_unit"),
        "reasons": reasons,
    }


def _audit_file(path: Path, area: str, project_root: Path) -> FileAudit:
    try:
        dataframe = load_csv(path)
    except CSVLoadError as exc:
        return FileAudit(
            path=str(path.relative_to(project_root)),
            area=area,
            record_count=None,
            error=str(exc),
        )

    fixture_marked = bool(is_test_fixture(dataframe, path))
    source_types = _nonblank_values(dataframe, "source_type")
    if "record_id" in dataframe.columns:
        record_ids = dataframe["record_id"].astype("string").str.strip()
        populated_ids = record_ids.notna() & record_ids.ne("")
        duplicate_record_ids = int(
            (record_ids[populated_ids].duplicated(keep=False)).sum()
        )
    else:
        duplicate_record_ids = 0
    duplicate_rows = int(dataframe.duplicated(keep=False).sum())

    provenance_complete = 0
    for _, row in dataframe.iterrows():
        source_type = str(row.get("source_type", "")).strip()
        required = ["source_type", *_PROVENANCE_FIELDS]
        if source_type == "literature":
            required.extend(("publication_title", "doi_or_url"))
            # A verified title or DOI/URL is enough as publication citation.
            citation_present = any(
                column in dataframe.columns
                and not pd.isna(row.get(column))
                and str(row.get(column)).strip()
                for column in ("publication_title", "doi_or_url")
            )
            complete = citation_present and all(
                column in dataframe.columns
                and not pd.isna(row.get(column))
                and str(row.get(column)).strip()
                for column in _PROVENANCE_FIELDS
            )
        else:
            complete = all(
                column in dataframe.columns
                and not pd.isna(row.get(column))
                and str(row.get(column)).strip()
                for column in required
            )
        provenance_complete += int(complete)

    valid = validate_dataframe(dataframe)
    invalid_ids = {
        issue.record_id for issue in valid.errors if issue.record_id is not None
    }
    # Invalid rows are never counted as modelling observations.
    data_for_readiness = dataframe[
        ~dataframe.get("record_id", pd.Series(index=dataframe.index, dtype="string"))
        .astype("string")
        .isin(invalid_ids)
    ].copy()
    if valid.errors and any(issue.record_id is None for issue in valid.errors):
        data_for_readiness = dataframe.iloc[0:0].copy()
    if dataframe.duplicated(keep=False).any():
        duplicate_mask = dataframe.duplicated(keep=False)
        data_for_readiness = data_for_readiness.loc[
            ~duplicate_mask.reindex(data_for_readiness.index, fill_value=False)
        ].copy()
    expected_source = {
        "raw_experimental": "experimental",
        "raw_literature": "literature",
    }.get(area)
    if expected_source is not None and (
        "source_type" not in data_for_readiness.columns
        or not (
            data_for_readiness["source_type"].astype(str).str.strip() == expected_source
        ).all()
    ):
        data_for_readiness = data_for_readiness.iloc[0:0].copy()
    if fixture_marked:
        data_for_readiness = data_for_readiness.iloc[0:0].copy()

    return FileAudit(
        path=str(path.relative_to(project_root)),
        area=area,
        record_count=len(dataframe),
        test_fixture_marked=fixture_marked,
        source_types=source_types,
        available_values={
            field_name: _nonblank_values(dataframe, field_name)
            for field_name in _SUMMARIZED_FIELDS
        },
        missing_value_counts=_missing_counts(dataframe),
        duplicate_record_ids=duplicate_record_ids,
        duplicate_rows=duplicate_rows,
        provenance_complete_records=provenance_complete,
        provenance_incomplete_records=len(dataframe) - provenance_complete,
        modelling_readiness={
            target: _target_readiness(data_for_readiness, target)
            for target in sorted(TEST_TYPES)
        },
    )


def audit_datasets(project_root: str | Path = ".") -> DatasetAudit:
    """Audit CSV files under raw experimental/literature and processed data.

    Test fixtures are outside these roots and are never discovered.
    """
    root = Path(project_root).resolve()
    paths: list[tuple[Path, str]] = []
    for relative, area in (
        (Path("data/raw/experimental"), "raw_experimental"),
        (Path("data/raw/literature"), "raw_literature"),
        (Path("data/processed"), "processed"),
    ):
        directory = root / relative
        if directory.exists():
            paths.extend(
                (path, area)
                for path in sorted(directory.rglob("*.csv"))
                if path.is_file()
                and path.name.casefold() != "source_register.csv"
            )
    audits = [_audit_file(path, area, root) for path, area in paths]
    register_path = root / "data" / "raw" / "literature" / "source_register.csv"
    register_entries = 0
    if register_path.is_file():
        try:
            register_entries = len(load_csv(register_path))
        except CSVLoadError:
            register_entries = 0
    raw_count = sum(item.area.startswith("raw_") for item in audits)
    usable_raw_count = sum(
        item.area.startswith("raw_")
        and not item.test_fixture_marked
        and item.record_count is not None
        and item.record_count > 0
        for item in audits
    )
    marked_count = sum(item.test_fixture_marked for item in audits)
    if usable_raw_count == 0:
        status = "No real raw observations found; the scientific dataset is empty."
        if marked_count:
            status += f" {marked_count} test/artificial fixture CSV(s) were excluded."
    else:
        status = (
            f"{usable_raw_count} unmarked raw CSV file(s) found; contents and provenance require "
            "review before use."
        )
        if marked_count:
            status += f" {marked_count} test/artificial fixture CSV(s) were excluded."
    return DatasetAudit(
        project_root=str(root),
        csv_file_count=len(audits),
        raw_experimental_csv_count=sum(item.area == "raw_experimental" for item in audits),
        raw_literature_csv_count=sum(item.area == "raw_literature" for item in audits),
        processed_csv_count=sum(item.area == "processed" for item in audits),
        literature_source_register_entries=register_entries,
        real_dataset_status=status,
        files=audits,
    )

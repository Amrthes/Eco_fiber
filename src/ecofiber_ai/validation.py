"""CSV loading, record validation, and machine-readable validation reports."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ecofiber_ai.schema import (
    CANONICAL_COLUMNS,
    NUMERIC_COLUMNS,
    OPTIONAL_NUMERIC_CONSTRAINTS,
    REQUIRED_COLUMNS,
    SUPPORTED_UNITS,
    TEXT_COLUMNS,
    TEST_TYPES,
    canonical_unit,
)


@dataclass(frozen=True)
class ValidationIssue:
    """One actionable validation finding."""

    severity: str
    code: str
    message: str
    record_id: str | None = None
    column: str | None = None


@dataclass
class ValidationReport:
    """Validation findings and record counts for one input dataset."""

    source_file: str | None
    record_count: int = 0
    valid_record_count: int = 0
    invalid_record_count: int = 0
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Whether the dataset has no validation errors."""
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report for JSON output."""
        return {
            "source_file": self.source_file,
            "record_count": self.record_count,
            "valid_record_count": self.valid_record_count,
            "invalid_record_count": self.invalid_record_count,
            "is_valid": self.is_valid,
            "errors": [asdict(issue) for issue in self.errors],
            "warnings": [asdict(issue) for issue in self.warnings],
        }

    def write_json(self, path: str | Path) -> Path:
        """Write this report as UTF-8 JSON and return the destination."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return destination


class CSVLoadError(ValueError):
    """Raised when an input CSV cannot be loaded safely."""


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a UTF-8 CSV, preserving field text and identifier spelling.

    Reading all columns as strings prevents identifiers such as ``0007`` from
    being silently converted to numbers. Measurement values are parsed during
    validation instead. Malformed or unreadable CSVs raise ``CSVLoadError``.
    """
    source = Path(path)
    try:
        return pd.read_csv(source, dtype="string", keep_default_na=False)
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise CSVLoadError(f"Could not read CSV '{source}': {exc}") from exc


def _is_blank(value: Any) -> bool:
    return pd.isna(value) or (isinstance(value, str) and not value.strip())


def _issue(
    report: ValidationReport,
    severity: str,
    code: str,
    message: str,
    *,
    record_id: str | None = None,
    column: str | None = None,
) -> None:
    issue = ValidationIssue(severity, code, message, record_id, column)
    (report.errors if severity == "error" else report.warnings).append(issue)


def validate_dataframe(
    dataframe: pd.DataFrame, *, source_file: str | None = None
) -> ValidationReport:
    """Validate a tidy measurement table without modifying or dropping rows.

    The required metadata columns must exist. Optional canonical columns may be
    absent or blank; blank optional metadata is reported as warnings. Every
    input row remains represented in the report counts and is left untouched.
    """
    report = ValidationReport(source_file=source_file, record_count=len(dataframe))
    if dataframe.empty:
        _issue(
            report,
            "error",
            "empty_dataset",
            "The CSV contains no observation records.",
        )
    missing_columns = [name for name in REQUIRED_COLUMNS if name not in dataframe.columns]
    for column in missing_columns:
        _issue(
            report,
            "error",
            "missing_required_column",
            f"Required column '{column}' is missing.",
            column=column,
        )

    for column in CANONICAL_COLUMNS:
        if column not in REQUIRED_COLUMNS and column not in dataframe.columns:
            _issue(
                report,
                "warning",
                "optional_column_absent",
                f"Optional metadata column '{column}' is absent.",
                column=column,
            )

    if missing_columns:
        report.invalid_record_count = len(dataframe)
        return report

    row_error_count: dict[int, int] = {index: 0 for index in range(len(dataframe))}
    seen_record_ids: dict[str, int] = {}
    seen_rows: set[tuple[Any, ...]] = set()
    source_types: set[str] = set()

    for position, (_, row) in enumerate(dataframe.iterrows()):
        raw_id = row["record_id"]
        record_id = None if _is_blank(raw_id) else str(raw_id).strip()
        for column in REQUIRED_COLUMNS:
            if _is_blank(row[column]):
                row_error_count[position] += 1
                _issue(
                    report,
                    "error",
                    "missing_required_value",
                    f"Required value in '{column}' is blank.",
                    record_id=record_id,
                    column=column,
                )

        for column in TEXT_COLUMNS:
            if column in dataframe.columns and not _is_blank(row[column]):
                if not isinstance(row[column], str):
                    row_error_count[position] += 1
                    _issue(
                        report,
                        "error",
                        "invalid_text_value",
                        f"'{column}' must be text.",
                        record_id=record_id,
                        column=column,
                    )

        if record_id is not None:
            if record_id in seen_record_ids:
                row_error_count[position] += 1
                _issue(
                    report,
                    "error",
                    "duplicate_record_id",
                    f"record_id '{record_id}' also appears in row "
                    f"{seen_record_ids[record_id] + 2} (CSV line numbering).",
                    record_id=record_id,
                    column="record_id",
                )
            else:
                seen_record_ids[record_id] = position

        row_tuple = tuple(
            None if _is_blank(value) else str(value).strip()
            for value in row.tolist()
        )
        if row_tuple in seen_rows:
            _issue(
                report,
                "warning",
                "duplicate_record",
                "This row duplicates an earlier complete row.",
                record_id=record_id,
            )
        else:
            seen_rows.add(row_tuple)

        source_type = "" if _is_blank(row["source_type"]) else str(row["source_type"]).strip()
        if source_type and source_type not in {"experimental", "literature"}:
            row_error_count[position] += 1
            _issue(
                report,
                "error",
                "invalid_source_type",
                "source_type must be 'experimental' or 'literature'.",
                record_id=record_id,
                column="source_type",
            )
        elif source_type:
            source_types.add(source_type)

        test_type = "" if _is_blank(row["test_type"]) else str(row["test_type"]).strip()
        if test_type and test_type not in TEST_TYPES:
            row_error_count[position] += 1
            _issue(
                report,
                "error",
                "unsupported_test_type",
                f"Unsupported test_type '{test_type}'.",
                record_id=record_id,
                column="test_type",
            )

        numeric_values: dict[str, float] = {}
        for column in NUMERIC_COLUMNS:
            if column not in dataframe.columns or _is_blank(row[column]):
                continue
            try:
                number = float(row[column])
            except (TypeError, ValueError, OverflowError):
                number = math.nan
            if not math.isfinite(number):
                row_error_count[position] += 1
                _issue(
                    report,
                    "error",
                    "invalid_numeric_value",
                    f"'{column}' must be a finite numeric value.",
                    record_id=record_id,
                    column=column,
                )
                continue
            numeric_values[column] = number

            if column in OPTIONAL_NUMERIC_CONSTRAINTS:
                minimum, maximum = OPTIONAL_NUMERIC_CONSTRAINTS[column]
                below_minimum = (
                    number <= minimum
                    if column == "fibre_length_mm"
                    else number < minimum
                )
                if below_minimum or (maximum is not None and number > maximum):
                    row_error_count[position] += 1
                    if column == "fibre_length_mm":
                        bound = "greater than 0"
                    elif maximum is not None:
                        bound = f"between {minimum:g} and {maximum:g}"
                    else:
                        bound = f"at least {minimum:g}"
                    _issue(
                        report,
                        "error",
                        "numeric_out_of_range",
                        f"'{column}' must be {bound}.",
                        record_id=record_id,
                        column=column,
                    )

        measured_value = numeric_values.get("measured_value")
        if measured_value is not None and test_type in TEST_TYPES:
            minimum = 0.0 if test_type in {"impact_resistance", "water_absorption"} else 0.0
            if measured_value < minimum or (
                test_type in {"tensile_strength", "flexural_strength"}
                and measured_value == minimum
            ):
                row_error_count[position] += 1
                _issue(
                    report,
                    "error",
                    "invalid_measurement_range",
                    (
                        "Strength measurements must be greater than zero; impact "
                        "resistance and water absorption must be zero or greater."
                    ),
                    record_id=record_id,
                    column="measured_value",
                )

        unit = "" if _is_blank(row["measured_unit"]) else str(row["measured_unit"]).strip()
        canonical = canonical_unit(unit) if unit else None
        if test_type in SUPPORTED_UNITS and unit:
            if canonical not in SUPPORTED_UNITS[test_type]:
                row_error_count[position] += 1
                allowed = ", ".join(sorted(SUPPORTED_UNITS[test_type]))
                _issue(
                    report,
                    "error",
                    "unsupported_unit",
                    f"Unit '{unit}' is not supported for {test_type}; use {allowed}.",
                    record_id=record_id,
                    column="measured_unit",
                )

        optional_metadata = {
            column: (
                row[column]
                if column in dataframe.columns
                else None
            )
            for column in ("fibre_type", "matrix_type", "test_standard")
        }
        for column, value in optional_metadata.items():
            if _is_blank(value):
                _issue(
                    report,
                    "warning",
                    "metadata_missing",
                    f"'{column}' is blank; compatibility cannot be fully assessed.",
                    record_id=record_id,
                    column=column,
                )

        if source_type == "literature":
            title = row.get("publication_title", "")
            citation = row.get("doi_or_url", "")
            if _is_blank(title) and _is_blank(citation):
                _issue(
                    report,
                    "warning",
                    "literature_citation_missing",
                    "Literature records should include publication_title and/or doi_or_url.",
                    record_id=record_id,
                    column="doi_or_url",
                )

    if len(source_types) > 1:
        _issue(
            report,
            "error",
            "mixed_source_types",
            "A source CSV must contain either experimental or literature records, not both.",
            column="source_type",
        )
        for position in row_error_count:
            row_error_count[position] += 1

    report.invalid_record_count = sum(count > 0 for count in row_error_count.values())
    report.valid_record_count = report.record_count - report.invalid_record_count
    return report


def validate_csv(path: str | Path) -> tuple[pd.DataFrame, ValidationReport]:
    """Load and validate a CSV, returning the original table and its report."""
    dataframe = load_csv(path)
    return dataframe, validate_dataframe(dataframe, source_file=str(Path(path)))

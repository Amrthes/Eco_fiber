"""Comparison reports for deciding whether two datasets merit review together."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

COMPARISON_FIELDS: tuple[str, ...] = (
    "test_type",
    "measured_unit",
    "matrix_type",
    "fibre_type",
    "fibre_form",
    "test_standard",
    "fabrication_method",
    "treatment_method",
    "naoh_concentration_pct",
    "fibre_loading_wt_pct",
)


@dataclass(frozen=True)
class CompatibilityFinding:
    """Dataset-level status for one potentially relevant condition."""

    field: str
    status: str
    left_values: tuple[str, ...]
    right_values: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class CompatibilityReport:
    """Non-binding review checklist; it never authorizes automatic merging."""

    findings: tuple[CompatibilityFinding, ...]
    review_required: bool = True
    automatic_merge_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_required": self.review_required,
            "automatic_merge_allowed": self.automatic_merge_allowed,
            "findings": [asdict(finding) for finding in self.findings],
        }


def _values(dataframe: pd.DataFrame, field: str) -> tuple[str, ...]:
    if field not in dataframe.columns:
        return ()
    values = {
        str(value).strip()
        for value in dataframe[field].tolist()
        if not pd.isna(value) and str(value).strip()
    }
    return tuple(sorted(values, key=str.casefold))


def compare_compatibility(
    left: pd.DataFrame, right: pd.DataFrame
) -> CompatibilityReport:
    """Flag condition differences and unavailable metadata between datasets.

    The report intentionally does not decide that datasets are scientifically
    interchangeable. A human must review property definitions, test methods,
    and the source papers before combining records.
    """
    findings: list[CompatibilityFinding] = []
    for field in COMPARISON_FIELDS:
        left_values = _values(left, field)
        right_values = _values(right, field)
        if not left_values or not right_values:
            status = "unassessed"
            message = f"Cannot compare '{field}' because metadata is missing on at least one side."
        elif left_values != right_values:
            status = "difference"
            message = f"'{field}' differs; review before considering combined analysis."
        else:
            status = "match"
            message = f"'{field}' values match in the supplied data."
        findings.append(
            CompatibilityFinding(
                field=field,
                status=status,
                left_values=left_values,
                right_values=right_values,
                message=message,
            )
        )
    return CompatibilityReport(findings=tuple(findings))

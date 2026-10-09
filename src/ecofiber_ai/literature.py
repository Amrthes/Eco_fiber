"""Source-register and literature-observation review workflow."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from ecofiber_ai.schema import SUPPORTED_UNITS, TEST_TYPES, canonical_unit
from ecofiber_ai.validation import CSVLoadError, load_csv, validate_dataframe
from ecofiber_ai.audit import MINIMUM_INDEPENDENT_GROUPS, MINIMUM_MODEL_RECORDS

SOURCE_REGISTER_COLUMNS = (
    "source_id",
    "title",
    "authors",
    "publication_year",
    "journal",
    "doi",
    "url",
    "metadata_source",
    "access_level",
    "fibre_type",
    "fibre_preparation",
    "matrix_type",
    "treatment_method",
    "naoh_concentration_pct",
    "fibre_loading_wt_pct",
    "fibre_length_mm",
    "fabrication_method",
    "test_methods",
    "test_standards",
    "reported_properties",
    "compatibility_category",
    "verification_status",
    "review_status",
    "review_notes",
    "extraction_confidence",
    "access_url",
    "access_date",
)
REVIEW_STATUSES = frozenset({"pending", "accepted", "rejected"})
COMPATIBILITY_CATEGORIES = frozenset(
    {
        "directly comparable",
        "conditionally comparable",
        "context only",
        "rejected",
    }
)
VERIFICATION_STATUSES = frozenset(
    {"unverified", "metadata_verified", "abstract_inspected", "full_text_inspected"}
)
ACCESS_LEVELS = frozenset({"metadata_only", "abstract_inspected", "full_text_inspected"})
EXTRACTION_TYPES = frozenset(
    {
        "individual",
        "reported_mean",
        "reported_range",
        "reported_value",
        "graph_estimate",
        "inferred",
    }
)
MODEL_ELIGIBLE_EXTRACTION_TYPES = frozenset(
    {"individual", "reported_mean", "reported_range"}
)
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


@dataclass(frozen=True)
class RegisterIssue:
    code: str
    message: str
    source_id: str | None = None
    field: str | None = None


@dataclass
class LiteratureReview:
    """Counts, validation findings and target readiness for curated sources."""

    source_register_path: str
    observations_path: str
    sources_discovered: int
    sources_verified: int
    verification_counts: dict[str, int]
    sources_reviewed: int
    sources_accepted: int
    sources_conditional: int
    sources_context_only: int
    sources_rejected: int
    duplicate_source_ids: int
    duplicate_papers: int
    observation_count: int
    provenance_complete_observations: int
    duplicate_measurement_ids: int
    duplicate_observation_rows: int
    source_reviews: list[dict[str, str]]
    compatible_observations_by_target: dict[str, int]
    observation_exclusions: dict[str, int]
    readiness: dict[str, dict[str, Any]]
    errors: list[RegisterIssue]
    warnings: list[RegisterIssue]
    data_gaps: list[str]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["errors"] = [asdict(issue) for issue in self.errors]
        result["warnings"] = [asdict(issue) for issue in self.warnings]
        return result

    def to_markdown(self) -> str:
        lines = [
            "# EcoFiber AI literature review",
            "",
            f"- Source register: `{self.source_register_path}`",
            f"- Observation table: `{self.observations_path}`",
            f"- Sources discovered: {self.sources_discovered}",
            f"- Sources with a non-unverified metadata/content record: {self.sources_verified}",
            "- Verification levels: "
            + "; ".join(
                f"{status.replace('_', ' ')}: {count}"
                for status, count in sorted(self.verification_counts.items())
            ),
            f"- Sources with review decisions (not pending): {self.sources_reviewed}",
            f"- Accepted sources: {self.sources_accepted}",
            f"- Conditionally comparable sources: {self.sources_conditional}",
            f"- Context-only sources: {self.sources_context_only}",
            f"- Rejected sources: {self.sources_rejected}",
            f"- Duplicate source IDs: {self.duplicate_source_ids}",
            f"- Duplicate DOI/paper identifiers: {self.duplicate_papers}",
            f"- Extracted observations: {self.observation_count}",
            f"- Observations with complete citation/material provenance: {self.provenance_complete_observations}",
            f"- Duplicate measurement IDs: {self.duplicate_measurement_ids}",
            f"- Duplicate complete observation rows: {self.duplicate_observation_rows}",
            "",
            "## Registered sources",
            "",
        ]
        for source in self.source_reviews:
            lines.append(
                f"- `{source['source_id']}` — {source['title']}; "
                f"verification: {source['verification_status']}; "
                f"access: {source['access_level']}; "
                f"compatibility: {source['compatibility_category']}; "
                f"review: {source['review_status']}. "
                f"Accessed {source['access_date']} at {source['access_url']}. "
                f"{source['review_notes']}"
            )
        if not self.source_reviews:
            lines.append("No source records are registered.")
        lines.extend(
            [
                "",
            "## Target compatibility and readiness",
            "",
            "| Target | Accepted directly comparable observations | Readiness | Details |",
            "|---|---:|---|---|",
            ]
        )
        for target in sorted(TEST_TYPES):
            target_readiness = self.readiness[target]
            status = "Potentially ready" if target_readiness["eligible"] else "Not ready"
            reasons = "; ".join(target_readiness["reasons"]) or "meets data checks"
            lines.append(
                f"| `{target}` | {self.compatible_observations_by_target[target]} "
                f"| {status} | {reasons} |"
            )
        lines.extend(["", "## Observation exclusions", ""])
        if self.observation_exclusions:
            lines.extend(
                f"- {reason}: {count}"
                for reason, count in sorted(self.observation_exclusions.items())
            )
        else:
            lines.append("No extracted rows were available to classify.")
        lines.extend(["", "## Data gaps", ""])
        lines.extend(f"- {gap}" for gap in self.data_gaps)
        if self.errors:
            lines.extend(["", "## Errors", ""])
            lines.extend(f"- `{issue.code}`: {issue.message}" for issue in self.errors)
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{issue.code}`: {issue.message}" for issue in self.warnings)
        return "\n".join(lines) + "\n"

    def write(self, directory: str | Path) -> tuple[Path, Path]:
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        markdown_path = destination / "literature_review.md"
        json_path = destination / "literature_review.json"
        markdown_path.write_text(self.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return markdown_path, json_path


def validate_source_register(register: pd.DataFrame) -> list[RegisterIssue]:
    """Validate bibliographic metadata and review classifications."""
    errors: list[RegisterIssue] = []
    missing_columns = [column for column in SOURCE_REGISTER_COLUMNS if column not in register.columns]
    for column in missing_columns:
        errors.append(
            RegisterIssue(
                "missing_register_column",
                f"Required source-register column '{column}' is missing.",
                field=column,
            )
        )
    if missing_columns:
        return errors

    source_ids = register["source_id"].astype("string").str.strip()
    for index, row in register.iterrows():
        source_id = str(row["source_id"]).strip() or None
        for field_name in (
            "source_id",
            "title",
            "metadata_source",
            "access_level",
            "access_url",
            "access_date",
        ):
            value = row[field_name]
            if pd.isna(value) or not str(value).strip():
                errors.append(
                    RegisterIssue(
                        "missing_register_value",
                        f"Required source-register value '{field_name}' is blank.",
                        source_id,
                        field_name,
                    )
                )
        if not _is_present(row.get("extraction_confidence", "")):
            errors.append(
                RegisterIssue(
                    "missing_extraction_confidence",
                    "Record extraction confidence, or explicitly state that it was not assessed.",
                    source_id,
                    "extraction_confidence",
                )
            )
        category = str(row["compatibility_category"]).strip()
        if category not in COMPATIBILITY_CATEGORIES:
            errors.append(
                RegisterIssue(
                    "invalid_compatibility_category",
                    f"Unsupported compatibility category '{category}'.",
                    source_id,
                    "compatibility_category",
                )
            )
        status = str(row["review_status"]).strip()
        verification = str(row["verification_status"]).strip()
        if status not in REVIEW_STATUSES:
            errors.append(
                RegisterIssue(
                    "invalid_review_status",
                    f"Unsupported review status '{status}'.",
                    source_id,
                    "review_status",
                )
            )
        access = str(row["access_level"]).strip()
        if access not in ACCESS_LEVELS:
            errors.append(
                RegisterIssue(
                    "invalid_access_level",
                    f"Unsupported access_level '{access}'.",
                    source_id,
                    "access_level",
                )
            )
        access_url = str(row["access_url"]).strip()
        if access_url and not access_url.casefold().startswith(("http://", "https://")):
            errors.append(
                RegisterIssue(
                    "invalid_access_url",
                    f"Access URL '{access_url}' must be an absolute HTTP(S) URL.",
                    source_id,
                    "access_url",
                )
            )
        access_date = str(row["access_date"]).strip()
        if access_date:
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", access_date):
                    raise ValueError
                date.fromisoformat(access_date)
            except ValueError:
                errors.append(
                    RegisterIssue(
                        "invalid_access_date",
                        f"Access date '{access_date}' must be a valid ISO date (YYYY-MM-DD).",
                        source_id,
                        "access_date",
                    )
                )
        if verification in {"abstract_inspected", "full_text_inspected"} and access != verification:
            errors.append(
                RegisterIssue(
                    "access_verification_mismatch",
                    "access_level must agree with the inspected content represented by verification_status.",
                    source_id,
                    "access_level",
                )
            )
        if verification not in VERIFICATION_STATUSES:
            errors.append(
                RegisterIssue(
                    "invalid_verification_status",
                    f"Unsupported verification status '{verification}'.",
                    source_id,
                    "verification_status",
                )
            )
        doi = str(row["doi"]).strip()
        url = str(row["url"]).strip()
        if verification != "unverified" and not (doi or url):
            errors.append(
                RegisterIssue(
                    "missing_verified_identifier",
                    "Verified source metadata requires a DOI or stable URL.",
                    source_id,
                    "doi",
                )
            )
        if doi:
            normalized_doi = re.sub(
                r"^https?://(?:dx\.)?doi\.org/",
                "",
                doi,
                flags=re.IGNORECASE,
            )
            if not DOI_PATTERN.fullmatch(normalized_doi):
                errors.append(
                    RegisterIssue(
                        "invalid_doi",
                        f"DOI '{doi}' does not have a valid DOI identifier form.",
                        source_id,
                        "doi",
                    )
                )
        if url and not url.casefold().startswith(("http://", "https://")):
            errors.append(
                RegisterIssue(
                    "invalid_source_url",
                    f"Source URL '{url}' must be an absolute HTTP(S) URL.",
                    source_id,
                    "url",
                )
            )
        if status == "accepted" and verification == "unverified":
            errors.append(
                RegisterIssue(
                    "unverified_source_accepted",
                    "An unverified source cannot be accepted.",
                    source_id,
                    "verification_status",
                )
            )
        if status == "accepted" and category in {"context only", "rejected"}:
            errors.append(
                RegisterIssue(
                    "inconsistent_acceptance",
                    f"A source classified '{category}' cannot have review_status='accepted'.",
                    source_id,
                    "review_status",
                )
            )

        year = row["publication_year"]
        if not pd.isna(year) and str(year).strip():
            try:
                parsed_year = int(str(year).strip())
                if parsed_year < 1400 or parsed_year > 2200:
                    raise ValueError
            except ValueError:
                errors.append(
                    RegisterIssue(
                        "invalid_publication_year",
                        f"Invalid publication year '{year}'.",
                        source_id,
                        "publication_year",
                    )
                )

    populated_ids = source_ids.notna() & source_ids.ne("")
    duplicated = source_ids[populated_ids].duplicated(keep=False)
    for index in source_ids[populated_ids][duplicated].index:
        errors.append(
            RegisterIssue(
                "duplicate_source_id",
                f"Duplicate source_id '{source_ids.loc[index]}'.",
                str(source_ids.loc[index]),
                "source_id",
            )
        )
    doi_values = register["doi"].astype("string").str.strip().str.casefold()
    doi_values = doi_values.str.replace(
        r"^https?://(dx\.)?doi\.org/", "", regex=True
    )
    populated_dois = doi_values.notna() & doi_values.ne("")
    for index in doi_values[populated_dois & doi_values.duplicated(keep=False)].index:
        errors.append(
            RegisterIssue(
                "duplicate_paper",
                f"Duplicate DOI '{doi_values.loc[index]}'.",
                str(source_ids.loc[index]) if not pd.isna(source_ids.loc[index]) else None,
                "doi",
            )
        )
    return errors


def _is_present(value: Any) -> bool:
    return not pd.isna(value) and bool(str(value).strip())


def _is_observation_provenance_complete(
    row: pd.Series, source_row: pd.Series | None
) -> bool:
    canonical_fields = (
        "record_id",
        "source_type",
        "source_id",
        "publication_title",
        "doi_or_url",
        "fibre_type",
        "matrix_type",
        "test_type",
        "test_standard",
        "measured_value",
        "measured_unit",
        "source_locator",
        "extraction_type",
    )
    if not all(_is_present(row.get(field, "")) for field in canonical_fields):
        return False
    if source_row is None or str(source_row.get("verification_status", "")) == "unverified":
        return False
    if str(row.get("publication_title", "")).strip().casefold() != str(
        source_row.get("title", "")
    ).strip().casefold():
        return False
    observation_citation = str(row.get("doi_or_url", "")).strip().casefold()
    registered_identifiers = {
        str(source_row.get(field, "")).strip().casefold()
        for field in ("doi", "url")
        if _is_present(source_row.get(field, ""))
    }
    normalized_observation = re.sub(
        r"^https?://(?:dx\.)?doi\.org/",
        "",
        observation_citation,
        flags=re.IGNORECASE,
    )
    normalized_registered = {
        re.sub(
            r"^https?://(?:dx\.)?doi\.org/",
            "",
            identifier,
            flags=re.IGNORECASE,
        )
        for identifier in registered_identifiers
    }
    return normalized_observation in normalized_registered


def _build_readiness(
    observations: pd.DataFrame,
    register_by_id: dict[str, pd.Series],
    target: str,
    *,
    blocked_ids: set[str] | None = None,
    blocked_rows: set[int] | None = None,
    register_valid: bool = True,
) -> tuple[int, dict[str, Any]]:
    eligible_rows: list[pd.Series] = []
    reasons: list[str] = []
    blocked_ids = blocked_ids or set()
    blocked_rows = blocked_rows or set()
    for index, row in observations.iterrows():
        if not register_valid or index in blocked_rows:
            continue
        if str(row.get("test_type", "")).strip() != target:
            continue
        source_id = str(row.get("source_id", "")).strip()
        if source_id in blocked_ids:
            continue
        source = register_by_id.get(source_id)
        if source is None:
            continue
        if (
            str(source.get("review_status", "")).strip() != "accepted"
            or str(source.get("compatibility_category", "")).strip()
            != "directly comparable"
            or str(source.get("verification_status", "")).strip() == "unverified"
            or str(row.get("review_status", "")).strip() != "accepted"
            or str(row.get("compatibility_category", "")).strip()
            != "directly comparable"
        ):
            continue
        extraction_type = str(row.get("extraction_type", "")).strip()
        if extraction_type not in MODEL_ELIGIBLE_EXTRACTION_TYPES:
            continue
        if not _is_observation_provenance_complete(row, source):
            continue
        unit = canonical_unit(str(row.get("measured_unit", "")))
        if unit not in SUPPORTED_UNITS[target]:
            continue
        if not all(
            _is_present(row.get(field, ""))
            for field in ("fibre_type", "matrix_type", "test_standard")
        ):
            continue
        if str(row.get("source_type", "")).strip() != "literature":
            continue
        value = pd.to_numeric(pd.Series([row.get("measured_value")]), errors="coerce").iloc[0]
        if pd.isna(value):
            continue
        try:
            if not math.isfinite(float(value)):
                continue
        except (TypeError, ValueError):
            continue
        eligible_rows.append(row)

    eligible = pd.DataFrame(eligible_rows)
    count = len(eligible)
    if count:
        for field_name in ("fibre_type", "matrix_type", "test_standard"):
            unique_values = {
                str(value).strip().casefold()
                for value in eligible[field_name].tolist()
                if _is_present(value)
            } if field_name in eligible.columns else set()
            if len(unique_values) != 1:
                reasons.append(
                    f"'{field_name}' differs or is missing across accepted observations"
                )
        unit_values = {
            canonical_unit(str(value))
            for value in eligible["measured_unit"].tolist()
            if _is_present(value)
        }
        if len(unit_values) != 1:
            reasons.append("target measurement units are mixed")
    if (
        not eligible.empty
        and "batch_id" in eligible.columns
        and eligible["batch_id"].map(_is_present).all()
    ):
        group_values = (
            eligible["source_id"].astype(str) + "::" + eligible["batch_id"].astype(str)
        )
        grouping = "source and batch"
    else:
        group_values = (
            eligible["source_id"].astype(str)
            if not eligible.empty and "source_id" in eligible.columns
            else pd.Series(dtype="string")
        )
        grouping = "source"
    group_count = int(group_values.nunique()) if count else 0
    if count < MINIMUM_MODEL_RECORDS:
        reasons.append(
            f"fewer than {MINIMUM_MODEL_RECORDS} accepted directly comparable observations ({count})"
        )
    if group_count < MINIMUM_INDEPENDENT_GROUPS:
        reasons.append(
            f"fewer than {MINIMUM_INDEPENDENT_GROUPS} independent {grouping} groups ({group_count})"
        )
    if not count:
        reasons.append("no accepted directly comparable extracted observations")
    return count, {
        "eligible": (
            count >= MINIMUM_MODEL_RECORDS
            and group_count >= MINIMUM_INDEPENDENT_GROUPS
            and not reasons
        ),
        "compatible_observation_count": count,
        "independent_groups": group_count,
        "grouping_strategy": grouping,
        "reasons": reasons,
    }


def review_literature(
    project_root: str | Path = ".",
    *,
    register_path: str | Path | None = None,
    observations_path: str | Path | None = None,
) -> LiteratureReview:
    """Read-only review of source register and extraction table."""
    root = Path(project_root).resolve()
    register_file = (
        Path(register_path)
        if register_path is not None
        else root / "data" / "raw" / "literature" / "source_register.csv"
    )
    observations_file = (
        Path(observations_path)
        if observations_path is not None
        else root / "data" / "raw" / "literature" / "literature_observations.csv"
    )
    if not register_file.is_absolute():
        register_file = root / register_file
    if not observations_file.is_absolute():
        observations_file = root / observations_file
    try:
        register = load_csv(register_file)
        observations = load_csv(observations_file)
    except CSVLoadError as exc:
        raise ValueError(str(exc)) from exc

    register_errors = validate_source_register(register)
    errors = list(register_errors)
    warnings: list[RegisterIssue] = []
    blocked_observation_ids: set[str] = set()
    blocked_observation_rows: set[int] = set()
    if len(observations):
        validation = validate_dataframe(observations)
        errors.extend(
            RegisterIssue(issue.code, issue.message, issue.record_id, issue.column)
            for issue in validation.errors
        )
        warnings.extend(
            RegisterIssue(issue.code, issue.message, issue.record_id, issue.column)
            for issue in validation.warnings
        )
        blocked_observation_ids.update(
            issue.record_id
            for issue in validation.errors
            if issue.record_id is not None
        )
        if any(issue.record_id is None for issue in validation.errors):
            blocked_observation_rows.update(observations.index.tolist())
        if "record_id" in observations.columns:
            record_ids = observations["record_id"].astype("string").str.strip()
            duplicate_id_mask = record_ids.notna() & record_ids.duplicated(keep=False)
            blocked_observation_ids.update(
                str(value) for value in record_ids[duplicate_id_mask].tolist()
            )
        duplicate_row_mask = observations.duplicated(keep=False)
        blocked_observation_rows.update(
            observations.index[duplicate_row_mask].tolist()
        )
        for index, row in observations.iterrows():
            review_status = str(row.get("review_status", "")).strip()
            category = str(row.get("compatibility_category", "")).strip()
            if review_status not in REVIEW_STATUSES or category not in COMPATIBILITY_CATEGORIES:
                errors.append(
                    RegisterIssue(
                        "invalid_observation_review",
                        "Observation must have a valid review_status and compatibility_category.",
                        str(row.get("record_id", "")).strip() or None,
                    )
                )
                blocked_observation_rows.add(index)
            extraction_type = str(row.get("extraction_type", "")).strip()
            if extraction_type not in EXTRACTION_TYPES:
                errors.append(
                    RegisterIssue(
                        "invalid_extraction_type",
                        "extraction_type must be individual, reported_mean, reported_range, "
                        "reported_value, graph_estimate, or inferred.",
                        str(row.get("record_id", "")).strip() or None,
                        "extraction_type",
                    )
                )
                blocked_observation_rows.add(index)
            if not _is_present(row.get("source_locator", "")):
                errors.append(
                    RegisterIssue(
                        "missing_source_locator",
                        "Each literature observation requires a page/table/figure/section locator.",
                        str(row.get("record_id", "")).strip() or None,
                        "source_locator",
                    )
                )
                blocked_observation_rows.add(index)
    elif not set(
        (
            "record_id",
            "source_type",
            "source_id",
            "test_type",
            "measured_value",
            "measured_unit",
        )
    ).issubset(observations.columns):
        errors.append(
            RegisterIssue(
                "missing_observation_schema",
                "The extraction table is missing canonical observation columns.",
            )
        )

    id_counts = register["source_id"].astype("string").str.strip().value_counts()
    register_by_id = {
        str(row["source_id"]).strip(): row
        for _, row in register.iterrows()
        if _is_present(row.get("source_id", ""))
    }
    duplicate_source_ids = int((id_counts[id_counts > 1].sum()))
    dois = register["doi"].astype("string").str.strip().str.casefold()
    dois = dois.str.replace(r"^https?://(dx\.)?doi\.org/", "", regex=True)
    duplicate_papers = int(dois[dois.notna() & dois.ne("")].duplicated(keep=False).sum())

    has_citation_identifier = register["doi"].astype("string").str.strip().ne("") | register[
        "url"
    ].astype("string").str.strip().ne("")
    verified = (
        register["verification_status"].isin(
            {"metadata_verified", "abstract_inspected", "full_text_inspected"}
        )
        & register["title"].astype("string").str.strip().ne("")
        & has_citation_identifier
    )
    reviewed = register["review_status"].isin({"accepted", "rejected"})
    accepted = register["review_status"].eq("accepted")
    conditional = register["compatibility_category"].eq("conditionally comparable")
    context = register["compatibility_category"].eq("context only")
    rejected = register["review_status"].eq("rejected") | register[
        "compatibility_category"
    ].eq("rejected")

    source_ids = set(register_by_id)
    exclusion_counts: dict[str, int] = {}
    duplicate_measurements = 0
    duplicate_rows = int(observations.duplicated(keep=False).sum())
    if "record_id" in observations.columns:
        ids = observations["record_id"].astype("string").str.strip()
        populated = ids.notna() & ids.ne("")
        duplicate_measurements = int(ids[populated & ids.duplicated(keep=False)].count())

    provenance_complete = 0
    for _, row in observations.iterrows():
        source_id = str(row.get("source_id", "")).strip()
        source = register_by_id.get(source_id)
        provenance_complete += int(_is_observation_provenance_complete(row, source))
        reasons: list[str] = []
        if source_id not in source_ids:
            reasons.append("observation source_id is absent from source register")
        elif str(source.get("verification_status", "")).strip() == "unverified":
            reasons.append("source is unverified")
        if source is not None and str(source.get("review_status", "")).strip() != "accepted":
            reasons.append(f"source review status is {source.get('review_status', 'missing')}")
        if source is not None and str(source.get("compatibility_category", "")).strip() != "directly comparable":
            reasons.append(
                "source compatibility category is "
                f"{source.get('compatibility_category', 'missing')}"
            )
        if str(row.get("review_status", "")).strip() != "accepted":
            reasons.append(f"observation review status is {row.get('review_status', 'missing')}")
        if str(row.get("compatibility_category", "")).strip() != "directly comparable":
            reasons.append("observation is not classified directly comparable")
        extraction_type = str(row.get("extraction_type", "")).strip()
        if extraction_type in EXTRACTION_TYPES and extraction_type not in MODEL_ELIGIBLE_EXTRACTION_TYPES:
            reasons.append(
                f"extraction type '{extraction_type}' is evidence-only and not eligible for training"
            )
        target = str(row.get("test_type", "")).strip()
        if target in TEST_TYPES:
            if canonical_unit(str(row.get("measured_unit", ""))) not in SUPPORTED_UNITS[target]:
                reasons.append("measurement unit is unsupported for the target")
            value = pd.to_numeric(pd.Series([row.get("measured_value")]), errors="coerce").iloc[0]
            if pd.isna(value) or not math.isfinite(float(value)):
                reasons.append("measurement value is missing or invalid")
        if not _is_observation_provenance_complete(row, source):
            reasons.append("source citation/material provenance is incomplete or mismatched")
        if reasons:
            for reason in set(reasons):
                exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1

    compatible: dict[str, int] = {}
    readiness: dict[str, dict[str, Any]] = {}
    for target in sorted(TEST_TYPES):
        compatible[target], readiness[target] = _build_readiness(
            observations,
            register_by_id,
            target,
            blocked_ids=blocked_observation_ids,
            blocked_rows=blocked_observation_rows,
            register_valid=not register_errors,
        )

    gaps: list[str] = []
    if not len(register):
        gaps.append("No literature sources are registered.")
    if not verified.any():
        gaps.append("No source has verified bibliographic metadata.")
    if not reviewed.any():
        gaps.append("No source has completed compatibility review.")
    if not len(observations):
        gaps.append("No numerical literature observations have been extracted.")
    if errors:
        gaps.append(
            "Correct source-register or observation-table validation errors before using literature records."
        )
    for target in sorted(TEST_TYPES):
        if not readiness[target]["eligible"]:
            gaps.append(f"{target}: " + "; ".join(readiness[target]["reasons"]))

    return LiteratureReview(
        source_register_path=str(register_file),
        observations_path=str(observations_file),
        sources_discovered=len(register),
        sources_verified=int(verified.sum()),
        verification_counts={
            status: int(register["verification_status"].eq(status).sum())
            for status in sorted(VERIFICATION_STATUSES)
        },
        sources_reviewed=int(reviewed.sum()),
        sources_accepted=int(accepted.sum()),
        sources_conditional=int(conditional.sum()),
        sources_context_only=int(context.sum()),
        sources_rejected=int(rejected.sum()),
        duplicate_source_ids=duplicate_source_ids,
        duplicate_papers=duplicate_papers,
        observation_count=len(observations),
        provenance_complete_observations=provenance_complete,
        duplicate_measurement_ids=duplicate_measurements,
        duplicate_observation_rows=duplicate_rows,
        source_reviews=[
            {
                field: str(row.get(field, "")).strip()
                for field in (
                    "source_id",
                    "title",
                    "verification_status",
                    "access_level",
                    "access_url",
                    "access_date",
                    "extraction_confidence",
                    "compatibility_category",
                    "review_status",
                    "review_notes",
                )
            }
            for _, row in register.iterrows()
        ],
        compatible_observations_by_target=compatible,
        observation_exclusions=exclusion_counts,
        readiness=readiness,
        errors=errors,
        warnings=warnings,
        data_gaps=gaps,
    )


def accepted_directly_comparable_source_ids(
    register_path: str | Path,
) -> set[str]:
    """Return model-eligible source IDs; invalid registers fail closed."""
    register = load_csv(register_path)
    issues = validate_source_register(register)
    if issues:
        raise ValueError(
            "Source register has validation errors; literature is blocked from modelling: "
            + "; ".join(issue.message for issue in issues[:5])
        )
    return {
        str(row["source_id"]).strip()
        for _, row in register.iterrows()
        if str(row["review_status"]).strip() == "accepted"
        and str(row["compatibility_category"]).strip() == "directly comparable"
        and str(row["verification_status"]).strip() != "unverified"
    }

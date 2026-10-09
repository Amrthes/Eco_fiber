"""Leakage-aware baseline regression with strict real-data provenance guards."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ecofiber_ai.audit import (
    MINIMUM_INDEPENDENT_GROUPS,
    MINIMUM_MODEL_RECORDS,
    is_test_fixture,
)
from ecofiber_ai.schema import SUPPORTED_UNITS, TEST_TYPES, canonical_unit
from ecofiber_ai.validation import CSVLoadError, load_csv, validate_dataframe

RANDOM_SEED = 42
NUMERIC_FEATURES = (
    "naoh_concentration_pct",
    "treatment_time_h",
    "fibre_loading_wt_pct",
    "fibre_length_mm",
)
CATEGORICAL_FEATURES = (
    "fibre_type",
    "matrix_type",
    "treatment_method",
    "fibre_form",
    "fabrication_method",
)
MINIMUM_TRAIN_RECORDS = 8
MINIMUM_TEST_RECORDS = 3


@dataclass
class ModelResult:
    """Evaluation result or actionable insufficient-data diagnostic."""

    target: str
    target_unit: str | None
    status: str
    message: str
    source_file: str | None = None
    input_record_count: int = 0
    eligible_record_count: int = 0
    excluded_record_count: int = 0
    excluded_records: list[dict[str, Any]] = field(default_factory=list)
    excluded_reasons: dict[str, int] = field(default_factory=dict)
    feature_columns: list[str] = field(default_factory=list)
    grouping_strategy: str | None = None
    independent_group_count: int = 0
    split_strategy: str | None = None
    train_record_count: int = 0
    test_record_count: int = 0
    metrics: dict[str, dict[str, float | None]] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    report_path: str | None = None
    model_path: str | None = None

    @property
    def trained(self) -> bool:
        return self.status == "evaluated"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_json(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.report_path = str(destination)
        destination.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return destination


class ModelDataError(ValueError):
    """Raised when the requested source cannot be safely used for modelling."""


def _contains_test_marker(frame: pd.DataFrame, path: Path) -> bool:
    return is_test_fixture(frame, path)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def discover_model_source(
    project_root: str | Path = ".", csv_path: str | Path | None = None
) -> Path:
    """Resolve exactly one raw CSV; never discover from processed/test data."""
    root = Path(project_root).resolve()
    permitted = (
        root / "data" / "raw" / "experimental",
        root / "data" / "raw" / "literature",
    )
    if csv_path is not None:
        candidate = Path(csv_path)
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        if not any(_is_within(candidate, directory) for directory in permitted):
            raise ModelDataError(
                "Model input must be a CSV inside data/raw/experimental/ or "
                "data/raw/literature/. Processed data and test fixtures are not training inputs."
            )
        if not candidate.is_file() or candidate.suffix.casefold() != ".csv":
            raise ModelDataError(f"Model input is not an existing CSV: {candidate}")
        return candidate

    discovered = sorted(
        path
        for directory in permitted
        if directory.exists()
        for path in directory.rglob("*.csv")
        if path.is_file()
        and path.resolve()
        != (root / "data" / "raw" / "literature" / "source_register.csv").resolve()
    )
    if not discovered:
        raise ModelDataError(
            "No raw scientific CSVs were found under data/raw/experimental/ or "
            "data/raw/literature/. Add actual, source-traceable measurements to the "
            "appropriate raw folder, then run validate, experimental review or literature "
            "review, and audit. No prediction or model will be produced without eligible data."
        )
    if len(discovered) != 1:
        raise ModelDataError(
            f"Found {len(discovered)} raw CSV files. They are not merged automatically; "
            "select one reviewed source with --csv."
        )
    return discovered[0]


def _preprocessor(features: list[str]) -> ColumnTransformer:
    numeric = [name for name in features if name in NUMERIC_FEATURES]
    categorical = [name for name in features if name in CATEGORICAL_FEATURES]
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def build_preprocessing_pipeline(features: list[str]) -> ColumnTransformer:
    """Public constructor for the shared numeric/categorical preprocessor."""
    if not features:
        raise ValueError("At least one supported feature is required.")
    unsupported = set(features) - set(NUMERIC_FEATURES) - set(CATEGORICAL_FEATURES)
    if unsupported:
        raise ValueError(f"Unsupported modelling features: {sorted(unsupported)}")
    return _preprocessor(features)


def _normalise_grouping(frame: pd.DataFrame) -> tuple[pd.Series | None, str | None]:
    source = frame["source_id"].astype("string").str.strip()
    if "batch_id" in frame.columns:
        batch = frame["batch_id"].astype("string").str.strip()
        if source.notna().all() and (source != "").all() and batch.notna().all() and (batch != "").all():
            return source + "::" + batch, "source_id+batch_id"
    if source.notna().all() and (source != "").all():
        return source, "source_id"
    return None, None


def _valid_record_mask(frame: pd.DataFrame, target: str) -> tuple[pd.Series, dict[str, int]]:
    excluded: dict[str, int] = {}
    mask = pd.Series(True, index=frame.index)
    validation = validate_dataframe(frame)
    invalid_ids = {
        issue.record_id for issue in validation.errors if issue.record_id is not None
    }
    if invalid_ids and "record_id" in frame.columns:
        invalid_rows = frame["record_id"].astype(str).isin(invalid_ids)
        excluded["validation errors (including duplicate identifiers)"] = int(invalid_rows.sum())
        mask &= ~invalid_rows
    if validation.errors and any(issue.record_id is None for issue in validation.errors):
        excluded["dataset-level schema errors"] = int(mask.sum())
        return pd.Series(False, index=frame.index), excluded

    target_rows = frame["test_type"].astype(str).str.strip() == target
    excluded["different target property"] = int((mask & ~target_rows).sum())
    mask &= target_rows

    numeric = pd.to_numeric(frame["measured_value"], errors="coerce")
    finite = numeric.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    excluded["missing or invalid target value"] = int((mask & ~finite).sum())
    mask &= finite

    canonical_units = frame["measured_unit"].astype(str).map(canonical_unit)
    supported_units = canonical_units.isin(SUPPORTED_UNITS[target])
    excluded["unsupported target unit"] = int((mask & ~supported_units).sum())
    mask &= supported_units

    for field_name in ("fibre_type", "matrix_type", "test_standard"):
        if field_name not in frame.columns:
            excluded[f"missing {field_name} metadata"] = int(mask.sum())
            return pd.Series(False, index=frame.index), excluded
        known = frame[field_name].astype("string").str.strip().ne("").fillna(False)
        excluded[f"missing {field_name} metadata"] = int((mask & ~known).sum())
        mask &= known
        if mask.any() and frame.loc[mask, field_name].nunique() != 1:
            excluded[f"incompatible {field_name} conditions"] = int(mask.sum())
            mask &= False

    for field_name in ("source_type", "source_id"):
        if field_name not in frame.columns:
            excluded[f"missing {field_name} metadata"] = int(mask.sum())
            return pd.Series(False, index=frame.index), excluded
        known = frame[field_name].astype("string").str.strip().ne("").fillna(False)
        excluded[f"missing {field_name} metadata"] = int((mask & ~known).sum())
        mask &= known
    if mask.any() and frame.loc[mask, "source_type"].astype(str).str.strip().eq("literature").any():
        citation_columns = [
            column for column in ("publication_title", "doi_or_url")
            if column in frame.columns
        ]
        if not citation_columns:
            excluded["missing literature citation"] = int(mask.sum())
            return pd.Series(False, index=frame.index), excluded
        citation = pd.Series(False, index=frame.index)
        for column in citation_columns:
            citation |= frame[column].astype("string").str.strip().ne("").fillna(False)
        missing_citation = mask & ~citation
        excluded["missing literature citation"] = int(missing_citation.sum())
        mask &= citation
    duplicate_rows = frame.duplicated(keep=False)
    if duplicate_rows.any():
        duplicate_count = int((mask & duplicate_rows).sum())
        if duplicate_count:
            excluded["duplicate complete rows"] = duplicate_count
            mask &= ~duplicate_rows
    if mask.any() and frame.loc[mask, "source_type"].nunique() != 1:
        excluded["mixed source types"] = int(mask.sum())
        mask &= False
    return mask, {key: count for key, count in excluded.items() if count}


def _excluded_record_details(
    frame: pd.DataFrame,
    eligible: pd.DataFrame,
    target: str,
    *,
    unit: str | None = None,
    additional_reasons: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Describe each filtered row by identifier and specific exclusion reasons."""
    eligible_indices = set(eligible.index)
    validation = validate_dataframe(frame)
    errors_by_id: dict[str, list[str]] = {}
    dataset_errors: list[str] = []
    for issue in validation.errors:
        if issue.record_id is None:
            dataset_errors.append(issue.message)
        else:
            errors_by_id.setdefault(issue.record_id, []).append(issue.message)

    target_rows = frame[
        frame.get("test_type", pd.Series("", index=frame.index)).astype(str).str.strip()
        == target
    ]
    varying_conditions = {
        column
        for column in ("fibre_type", "matrix_type", "test_standard")
        if column in target_rows.columns and target_rows[column].nunique() > 1
    }
    rows: list[dict[str, Any]] = []
    for row_number, (index, row) in enumerate(frame.iterrows(), start=1):
        if index in eligible_indices:
            continue
        identifier_value = row.get("record_id")
        identifier = (
            None
            if pd.isna(identifier_value) or not str(identifier_value).strip()
            else str(identifier_value).strip()
        )
        reasons = list(errors_by_id.get(identifier or "", []))
        if identifier and additional_reasons and identifier in additional_reasons:
            reasons.append(additional_reasons[identifier])
        if dataset_errors:
            reasons.extend(dataset_errors)
        row_target = str(row.get("test_type", "")).strip()
        if row_target != target:
            reasons.append(f"target is '{row_target or 'missing'}', not '{target}'")
        else:
            try:
                value = float(row.get("measured_value"))
                if not math.isfinite(value):
                    raise ValueError
            except (TypeError, ValueError, OverflowError):
                reasons.append("target value is missing or non-finite")
            row_unit = canonical_unit(str(row.get("measured_unit", "")))
            if row_unit not in SUPPORTED_UNITS[target]:
                reasons.append("target unit is unsupported")
            elif unit is not None and row_unit != unit:
                reasons.append(f"unit '{row_unit}' differs from selected unit '{unit}'")
            for column in varying_conditions:
                reasons.append(f"'{column}' differs within the source target observations")
            for column in ("fibre_type", "matrix_type", "test_standard", "source_type", "source_id"):
                value = row.get(column)
                if pd.isna(value) or not str(value).strip():
                    reasons.append(f"required modelling metadata '{column}' is missing")
            source_type = str(row.get("source_type", "")).strip()
            if source_type == "literature" and not any(
                not pd.isna(row.get(column))
                and str(row.get(column)).strip()
                for column in ("publication_title", "doi_or_url")
            ):
                reasons.append("literature publication citation is missing")
        if frame.duplicated(keep=False).loc[index]:
            reasons.append("complete row is duplicated")
        if not reasons:
            reasons.append("excluded by dataset-level compatibility or validation requirements")
        rows.append(
            {
                "record_id": identifier,
                "row_number": row_number,
                "reasons": sorted(set(reasons)),
            }
        )
    return rows


def _feature_columns(frame: pd.DataFrame) -> list[str]:
    available: list[str] = []
    for name in (*NUMERIC_FEATURES, *CATEGORICAL_FEATURES):
        if name not in frame.columns:
            continue
        values = frame[name]
        if name in NUMERIC_FEATURES:
            usable = pd.to_numeric(values, errors="coerce").notna().any()
        else:
            usable = values.astype("string").str.strip().ne("").fillna(False).any()
        if usable:
            available.append(name)
    return available


def _metrics(actual: np.ndarray, predicted: np.ndarray, groups: pd.Series) -> dict[str, float | None]:
    r2: float | None = None
    if len(actual) >= 2 and groups.nunique() >= 2 and np.unique(actual).size >= 2:
        r2 = float(r2_score(actual, predicted))
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": r2,
    }


def evaluate_grouped_models(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    features: list[str],
    *,
    random_state: int = RANDOM_SEED,
) -> tuple[dict[str, dict[str, float | None]], int, int, pd.Series]:
    """Evaluate baselines on one deterministic group-isolated holdout.

    This low-level helper assumes its input rows have already passed the
    scientific-data provenance and sufficiency gates in ``run_baseline``.
    """
    splitter = GroupShuffleSplit(
        n_splits=1, test_size=0.25, random_state=random_state
    )
    train_indices, test_indices = next(splitter.split(X, y, groups=groups))
    if (
        len(train_indices) < MINIMUM_TRAIN_RECORDS
        or len(test_indices) < MINIMUM_TEST_RECORDS
        or groups.iloc[train_indices].nunique() < 2
        or groups.iloc[test_indices].nunique() < 1
    ):
        raise ValueError(
            "Grouped holdout did not leave enough independent training and test "
            "observations; add more specimens across independent batches."
        )
    X_train, X_test = X.iloc[train_indices], X.iloc[test_indices]
    y_train, y_test = y.iloc[train_indices], y.iloc[test_indices]
    test_groups = groups.iloc[test_indices]
    candidates: dict[str, Any] = {
        "dummy_mean": DummyRegressor(strategy="mean"),
        "linear_regression": LinearRegression(),
    }
    if len(train_indices) >= 10:
        candidates["random_forest"] = RandomForestRegressor(
            n_estimators=200,
            random_state=random_state,
            n_jobs=1,
            min_samples_leaf=2,
        )

    metrics: dict[str, dict[str, float | None]] = {}
    for name, estimator in candidates.items():
        pipeline = Pipeline(
            [
                ("preprocessor", build_preprocessing_pipeline(features)),
                ("regressor", estimator),
            ]
        )
        pipeline.fit(X_train, y_train)
        prediction = pipeline.predict(X_test)
        metrics[name] = _metrics(
            y_test.to_numpy(dtype=float),
            np.asarray(prediction, dtype=float),
            test_groups,
        )
    return metrics, len(train_indices), len(test_indices), test_groups


def run_baseline(
    target: str,
    *,
    project_root: str | Path = ".",
    csv_path: str | Path | None = None,
    unit: str | None = None,
    output_dir: str | Path | None = None,
    model_dir: str | Path | None = None,
) -> ModelResult:
    """Run one deterministic grouped holdout after strict data sufficiency checks."""
    if target not in TEST_TYPES:
        raise ModelDataError(
            f"Unsupported target '{target}'. Choose one of: {', '.join(sorted(TEST_TYPES))}."
        )
    try:
        source = discover_model_source(project_root, csv_path)
    except ModelDataError as exc:
        return _write_result(
            ModelResult(
                target=target,
                target_unit=None,
                status="insufficient_data",
                message=str(exc),
                limitations=[
                    "No real dataset is inferred or fabricated when source files are absent."
                ],
            ),
            output_dir,
            project_root=project_root,
        )
    frame = load_csv(source)
    if _contains_test_marker(frame, source):
        raise ModelDataError(
            "Test/artificial/synthetic fixture markers were found. Test data cannot enter "
            "the scientific modelling workflow."
        )
    relative_to_root = source.relative_to(Path(project_root).resolve())
    source_folder = relative_to_root.parts[2]
    if "source_type" not in frame.columns or not (
        frame["source_type"].astype(str).str.strip() == source_folder
    ).all():
        raise ModelDataError(
            f"CSV location says source_type='{source_folder}', but its records do not all "
            "match. Keep experimental and literature sources separate."
        )

    mask, excluded = _valid_record_mask(frame, target)
    eligible = frame.loc[mask].copy()
    additional_exclusion_reasons: dict[str, str] = {}
    if source_folder == "experimental" and not eligible.empty:
        from ecofiber_ai.experimental import review_experimental_csv

        quality = review_experimental_csv(source)
        decisions_by_id = {
            decision.record_id: decision
            for decision in quality.decisions
            if decision.record_id
        }
        accepted_ids = {
            record_id
            for record_id, decision in decisions_by_id.items()
            if decision.status == "accepted"
        }
        accepted = eligible["record_id"].astype(str).isin(accepted_ids)
        excluded["experimental quality review did not accept the record"] = int(
            (~accepted).sum()
        )
        for record_id in eligible.loc[~accepted, "record_id"].astype(str):
            decision = decisions_by_id.get(record_id)
            additional_exclusion_reasons[record_id] = (
                "; ".join(decision.reasons)
                if decision is not None
                else "no accepted experimental quality-review decision"
            )
        eligible = eligible.loc[accepted].copy()
    if source_folder == "literature":
        from ecofiber_ai.literature import (
            MODEL_ELIGIBLE_EXTRACTION_TYPES,
            accepted_directly_comparable_source_ids,
        )

        register_path = (
            Path(project_root).resolve()
            / "data"
            / "raw"
            / "literature"
            / "source_register.csv"
        )
        if not register_path.is_file():
            raise ModelDataError(
                "Literature modelling requires data/raw/literature/source_register.csv "
                "with reviewed source classifications."
            )
        try:
            accepted_sources = accepted_directly_comparable_source_ids(register_path)
        except ValueError as exc:
            raise ModelDataError(str(exc)) from exc
        if "review_status" not in eligible.columns or "compatibility_category" not in eligible.columns:
            eligible = eligible.iloc[0:0].copy()
            excluded["missing literature review fields"] = int(mask.sum())
        else:
            source_allowed = eligible["source_id"].astype(str).isin(accepted_sources)
            row_accepted = (
                eligible["review_status"].astype(str).str.strip().eq("accepted")
                & eligible["compatibility_category"]
                .astype(str)
                .str.strip()
                .eq("directly comparable")
            )
            allowed = source_allowed & row_accepted
            excluded["literature source not accepted as directly comparable"] = int(
                (~allowed).sum()
            )
            for index in eligible.index[~allowed]:
                record_id = str(eligible.loc[index, "record_id"]).strip()
                additional_exclusion_reasons[record_id] = (
                    "source or observation is not explicitly accepted as directly comparable"
                )
            eligible = eligible.loc[allowed].copy()
        if "extraction_type" not in eligible.columns:
            evidence_allowed = pd.Series(False, index=eligible.index)
        else:
            evidence_allowed = eligible["extraction_type"].astype(str).str.strip().isin(
                MODEL_ELIGIBLE_EXTRACTION_TYPES
            )
        excluded["literature evidence type is not eligible for training"] = int(
            (~evidence_allowed).sum()
        )
        for index in eligible.index[~evidence_allowed]:
            record_id = str(eligible.loc[index, "record_id"]).strip()
            extraction_type = str(eligible.loc[index, "extraction_type"]).strip()
            additional_exclusion_reasons[record_id] = (
                f"extraction type '{extraction_type or 'missing'}' is evidence-only "
                "and not eligible for training"
            )
        eligible = eligible.loc[evidence_allowed].copy()
    canonical_units = {
        canonical_unit(str(value))
        for value in eligible["measured_unit"].tolist()
        if canonical_unit(str(value)) is not None
    }
    if unit is not None:
        requested_unit = canonical_unit(unit)
        if requested_unit not in SUPPORTED_UNITS[target]:
            raise ModelDataError(
                f"Unit '{unit}' is not supported for {target}; accepted units are "
                f"{', '.join(sorted(SUPPORTED_UNITS[target]))}."
            )
        wrong_unit = eligible["measured_unit"].astype(str).map(canonical_unit) != requested_unit
        excluded["different requested unit"] = int(wrong_unit.sum())
        eligible = eligible.loc[~wrong_unit].copy()
        target_unit = requested_unit
    elif len(canonical_units) == 1:
        target_unit = next(iter(canonical_units))
    elif len(canonical_units) > 1:
        result = ModelResult(
            target=target,
            target_unit=None,
            status="insufficient_data",
            message="Multiple incompatible units are present; specify --unit to select one.",
            source_file=str(source),
            input_record_count=len(frame),
            eligible_record_count=len(eligible),
            excluded_record_count=len(frame) - len(eligible),
            excluded_reasons=excluded,
            limitations=["Units are not converted unless an explicit compatible conversion exists."],
            excluded_records=_excluded_record_details(
                frame, eligible.iloc[0:0], target
            ),
        )
        return _write_result(result, output_dir, project_root=project_root)
    else:
        target_unit = None

    features = _feature_columns(eligible)
    base_result = ModelResult(
        target=target,
        target_unit=target_unit,
        status="insufficient_data",
        message="Insufficient validated, compatible real observations for leakage-aware evaluation.",
        source_file=str(source),
        input_record_count=len(frame),
        eligible_record_count=len(eligible),
        excluded_record_count=len(frame) - len(eligible),
        excluded_records=_excluded_record_details(
            frame,
            eligible,
            target,
            unit=target_unit,
            additional_reasons=additional_exclusion_reasons,
        ),
        excluded_reasons=excluded,
        feature_columns=features,
        limitations=[
            "No study-level generalization claim is made from one raw source file.",
            "A single grouped holdout is a screening estimate, not a final model-selection study.",
        ],
    )
    if target_unit is None:
        base_result.message = (
            "No compatible target values with recognized units were found. Add real "
            "measurements for this property, preserve the reported units, and rerun "
            "validation and readiness review; no prediction was generated."
        )
        return _write_result(base_result, output_dir, project_root=project_root)
    if not features:
        base_result.message = "No non-empty scientifically meaningful predictor features are available."
        return _write_result(base_result, output_dir, project_root=project_root)
    grouping, grouping_strategy = _normalise_grouping(eligible)
    if grouping is None:
        base_result.message = (
            "No complete batch/source grouping metadata is available; leakage-resistant "
            "validation cannot be formed."
        )
        return _write_result(base_result, output_dir, project_root=project_root)
    group_count = int(grouping.nunique())
    base_result.grouping_strategy = grouping_strategy
    base_result.independent_group_count = group_count
    if len(eligible) < MINIMUM_MODEL_RECORDS or group_count < MINIMUM_INDEPENDENT_GROUPS:
        base_result.message = (
            f"Need at least {MINIMUM_MODEL_RECORDS} compatible observations and "
            f"{MINIMUM_INDEPENDENT_GROUPS} independent {grouping_strategy} groups; "
            f"found {len(eligible)} observations and {group_count} groups. Add real "
            "independent observations and rerun readiness checks; no prediction was generated."
        )
        return _write_result(base_result, output_dir, project_root=project_root)

    X = eligible[features].copy()
    for name in NUMERIC_FEATURES:
        if name in X.columns:
            X[name] = pd.to_numeric(X[name], errors="coerce").astype(float)
    for name in CATEGORICAL_FEATURES:
        if name in X.columns:
            X[name] = X[name].astype("object").replace("", np.nan)
    y = pd.to_numeric(eligible["measured_value"], errors="coerce").astype(float)
    try:
        (
            base_result.metrics,
            base_result.train_record_count,
            base_result.test_record_count,
            test_groups,
        ) = evaluate_grouped_models(
            X,
            y,
            grouping,
            features,
            random_state=RANDOM_SEED,
            )
    except (ValueError, TypeError) as exc:
        base_result.message = f"Model evaluation could not be completed: {exc}"
        base_result.status = "insufficient_data"
        return _write_result(base_result, output_dir, project_root=project_root)

    # Save the interpretable baseline trained on all eligible data after evaluation.
    final_baseline = Pipeline(
        [
            ("preprocessor", build_preprocessing_pipeline(features)),
            ("regressor", DummyRegressor(strategy="mean")),
        ]
    )
    final_baseline.fit(X, y)
    base_result.status = "evaluated"
    base_result.message = (
        "Grouped holdout evaluation completed. Metrics describe this source only and "
        "do not establish broad generalization."
    )
    base_result.split_strategy = (
        f"One GroupShuffleSplit holdout (25% test groups, random_state={RANDOM_SEED}); "
        f"groups are {grouping_strategy}."
    )
    if test_groups.nunique() < 2:
        base_result.limitations.append(
            "Only one independent group is represented in the holdout; R² is omitted."
        )
    if output_dir is not None:
        report_directory = Path(output_dir)
    else:
        report_directory = Path(project_root) / "data" / "processed" / "models"
    model_directory = (
        Path(model_dir)
        if model_dir is not None
        else Path(project_root) / "models"
    )
    safe_target = re.sub(r"[^A-Za-z0-9_-]+", "_", target)
    model_path = model_directory / f"{safe_target}_dummy_baseline.joblib"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_baseline, model_path)
    base_result.model_path = str(model_path)
    return _write_result(base_result, report_directory, project_root=project_root)


def _write_result(
    result: ModelResult,
    output_dir: str | Path | None,
    *,
    project_root: str | Path = ".",
) -> ModelResult:
    if output_dir is not None:
        directory = Path(output_dir)
    else:
        directory = Path(project_root) / "data" / "processed" / "models"
    safe_target = re.sub(r"[^A-Za-z0-9_-]+", "_", result.target)
    result.write_json(directory / f"{safe_target}_baseline_report.json")
    return result

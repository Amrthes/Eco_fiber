"""Command-line entry point for EcoFiber AI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ecofiber_ai.schema import TEST_TYPES
from ecofiber_ai.validation import CSVLoadError, validate_csv


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ecofiber_ai")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser(
        "validate", help="validate one input CSV and write a report"
    )
    validate.add_argument("csv", type=Path, help="path to one source CSV")
    validate.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
        help="processed-output root (default: data/processed)",
    )
    audit = commands.add_parser(
        "audit", help="inventory research CSVs and report modelling readiness"
    )
    audit.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="project root containing data/ (default: current directory)",
    )
    audit.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
        help="report directory (default: data/processed)",
    )
    audit.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="audit report format (default: markdown)",
    )
    model = commands.add_parser(
        "model", help="evaluate a leakage-aware baseline for one raw source CSV"
    )
    model.add_argument(
        "--target",
        required=True,
        choices=tuple(sorted(TEST_TYPES)),
        help="target property from the canonical schema",
    )
    model.add_argument(
        "--csv",
        type=Path,
        help="one reviewed CSV under data/raw/experimental/ or data/raw/literature/",
    )
    model.add_argument(
        "--unit",
        help="select one accepted target unit when multiple compatible unit groups exist",
    )
    model.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="project root containing data/ (default: current directory)",
    )
    model.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/models"),
        help="JSON report directory (default: data/processed/models)",
    )
    model.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models"),
        help="trained baseline model directory (default: models)",
    )
    literature = commands.add_parser(
        "literature", help="review source provenance and curated literature observations"
    )
    literature_commands = literature.add_subparsers(
        dest="literature_command", required=True
    )
    literature_review = literature_commands.add_parser(
        "review", help="validate the source register and report extraction readiness"
    )
    literature_review.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="project root containing data/ (default: current directory)",
    )
    literature_review.add_argument(
        "--register",
        type=Path,
        help="source-register CSV (default: data/raw/literature/source_register.csv)",
    )
    literature_review.add_argument(
        "--observations",
        type=Path,
        help="extracted observations CSV (default: data/raw/literature/literature_observations.csv)",
    )
    literature_review.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/literature-review"),
        help="report directory (default: data/processed/literature-review)",
    )
    experimental = commands.add_parser(
        "experimental",
        help="quality-review experimental observations without changing the raw CSV",
    )
    experimental_commands = experimental.add_subparsers(
        dest="experimental_command", required=True
    )
    experimental_review = experimental_commands.add_parser(
        "review", help="classify experimental records and summarize target readiness"
    )
    experimental_review.add_argument(
        "csv", type=Path, help="experimental observation CSV to review"
    )
    experimental_review.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/experimental-review"),
        help="report directory (default: data/processed/experimental-review)",
    )
    readiness = commands.add_parser(
        "readiness",
        help="run a non-training end-to-end data and model-readiness demo",
    )
    readiness.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="project root containing data/ (default: current directory)",
    )
    readiness.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/readiness"),
        help="readiness report directory (default: data/processed/readiness)",
    )
    eligibility = commands.add_parser(
        "eligibility",
        help="generate human-readable and machine-readable evidence eligibility audit",
    )
    eligibility.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="project root containing data/ (default: current directory)",
    )
    eligibility.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
        help="report directory (default: data/processed)",
    )
    predict = commands.add_parser(
        "predict",
        help="predict composite properties with readiness gates and validation",
    )
    predict.add_argument(
        "--target",
        required=True,
        choices=tuple(sorted(TEST_TYPES)),
        help="target property to predict",
    )
    predict.add_argument(
        "--fibre-loading",
        type=float,
        required=True,
        help="fibre loading in weight percentage (wt%)",
    )
    predict.add_argument(
        "--naoh-conc",
        type=float,
        default=0.0,
        help="NaOH treatment concentration in percentage (default: 0.0)",
    )
    predict.add_argument(
        "--treatment-time",
        type=float,
        default=0.0,
        help="NaOH treatment duration in hours (default: 0.0)",
    )
    predict.add_argument(
        "--fibre-length",
        type=float,
        default=10.0,
        help="fibre length in mm (default: 10.0)",
    )
    predict.add_argument(
        "--demo-mode",
        action="store_true",
        help="enable software demo benchmark simulation for testing UI/workflow",
    )
    predict.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="project root containing data/ (default: current directory)",
    )
    dashboard = commands.add_parser(
        "dashboard",
        help="launch interactive Streamlit application",
    )
    dashboard.add_argument(
        "--port",
        type=int,
        default=8501,
        help="port to run Streamlit on (default: 8501)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested workflow and return a process exit code."""
    args = _parser().parse_args(argv)
    if args.command == "validate":
        try:
            dataframe, report = validate_csv(args.csv)
        except CSVLoadError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        source_types = (
            set(dataframe["source_type"].dropna().astype(str).str.strip())
            if "source_type" in dataframe.columns
            else set()
        )
        source_types.discard("")
        source_folder = (
            next(iter(source_types))
            if len(source_types) == 1 and next(iter(source_types)) in {"experimental", "literature"}
            else "unclassified"
        )
        output_directory = args.output_dir / source_folder
        output_directory.mkdir(parents=True, exist_ok=True)
        output_csv = output_directory / f"{args.csv.stem}.validated.csv"
        output_report = output_directory / f"{args.csv.stem}.validation.json"

        # Preserve every original row and column; validation never filters data.
        dataframe.to_csv(output_csv, index=False)
        report.write_json(output_report)
        print(
            f"Records: {report.record_count}; valid: {report.valid_record_count}; "
            f"invalid: {report.invalid_record_count}; "
            f"errors: {len(report.errors)}; warnings: {len(report.warnings)}"
        )
        print(f"Validated copy: {output_csv}")
        print(f"Report: {output_report}")
        return 0 if report.is_valid else 1
    if args.command == "audit":
        from ecofiber_ai.audit import audit_datasets

        result = audit_datasets(args.project_root)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if args.format == "json":
            destination = result.write_json(args.output_dir / "dataset_audit.json")
        else:
            destination = result.write_markdown(args.output_dir / "dataset_audit.md")
        print(result.real_dataset_status)
        print(
            f"CSV files: {result.csv_file_count} "
            f"(experimental: {result.raw_experimental_csv_count}, "
            f"literature: {result.raw_literature_csv_count}, "
            f"processed: {result.processed_csv_count})"
        )
        print(f"Audit report: {destination}")
        return 0
    if args.command == "model":
        from ecofiber_ai.modeling import ModelDataError, run_baseline

        try:
            result = run_baseline(
                args.target,
                project_root=args.project_root,
                csv_path=args.csv,
                unit=args.unit,
                output_dir=args.output_dir,
                model_dir=args.model_dir,
            )
        except (ModelDataError, CSVLoadError) as exc:
            print(f"Model not run: {exc}", file=sys.stderr)
            return 1
        print(result.message)
        print(
            f"Records: {result.eligible_record_count} eligible of "
            f"{result.input_record_count}; excluded: {result.excluded_record_count}"
        )
        if result.report_path:
            print(f"Report: {result.report_path}")
        if result.model_path:
            print(f"Baseline model: {result.model_path}")
        for name, metrics in result.metrics.items():
            print(
                f"{name}: MAE={metrics['mae']:.6g}, RMSE={metrics['rmse']:.6g}, "
                f"R2={metrics['r2'] if metrics['r2'] is not None else 'not reported'}"
            )
        return 0 if result.trained else 1
    if args.command == "literature":
        from ecofiber_ai.literature import review_literature

        try:
            result = review_literature(
                project_root=args.project_root,
                register_path=args.register,
                observations_path=args.observations,
            )
        except ValueError as exc:
            print(f"Literature review failed: {exc}", file=sys.stderr)
            return 2
        markdown_path, json_path = result.write(args.output_dir)
        print(
            f"Sources: {result.sources_discovered}; with metadata/content verification: "
            f"{result.sources_verified}; "
            f"with review decisions: {result.sources_reviewed}; "
            f"accepted: {result.sources_accepted}; "
            f"conditional: {result.sources_conditional}; context-only: "
            f"{result.sources_context_only}; rejected: {result.sources_rejected}"
        )
        print(
            f"Observations: {result.observation_count}; provenance complete: "
            f"{result.provenance_complete_observations}"
        )
        print(f"Markdown report: {markdown_path}")
        print(f"JSON report: {json_path}")
        return 1 if result.errors else 0
    if args.command == "experimental":
        from ecofiber_ai.experimental import review_experimental_csv

        try:
            result = review_experimental_csv(args.csv)
        except CSVLoadError as exc:
            print(f"Experimental review failed: {exc}", file=sys.stderr)
            return 2
        markdown_path, json_path = result.write(args.output_dir)
        print(
            f"Records: {result.record_count}; accepted: {result.accepted_count}; "
            f"review: {result.review_count}; rejected: {result.rejected_count}"
        )
        print(f"Markdown report: {markdown_path}")
        print(f"JSON report: {json_path}")
        return 0
    if args.command == "readiness":
        from ecofiber_ai.readiness import build_readiness_report

        try:
            result = build_readiness_report(args.project_root)
        except (CSVLoadError, ValueError) as exc:
            print(f"Readiness report failed: {exc}", file=sys.stderr)
            return 2
        markdown_path, json_path = result.write(args.output_dir)
        print(result.demo_status)
        print(f"Readiness report: {markdown_path}")
        print(f"JSON report: {json_path}")
        return 0
    if args.command == "eligibility":
        from ecofiber_ai.eligibility import build_eligibility_audit

        try:
            result = build_eligibility_audit(args.project_root)
        except (CSVLoadError, ValueError) as exc:
            print(f"Eligibility audit failed: {exc}", file=sys.stderr)
            return 2
        markdown_path = result.write_markdown(args.output_dir / "eligibility_audit.md")
        json_path = result.write_json(args.output_dir / "eligibility_audit.json")
        print(result.audit_verdict)
        print(
            f"Sources: {result.total_registered_sources}; "
            f"Extracted observations: {result.total_normalized_observations}; "
            f"Accepted compatible: {result.total_accepted_compatible_observations}; "
            f"Unready targets: {result.unready_target_count}/4"
        )
        print(f"Markdown report: {markdown_path}")
        print(f"JSON report: {json_path}")
        return 0
    if args.command == "predict":
        from ecofiber_ai.inference import PredictionInput, predict_property

        inp = PredictionInput(
            target=args.target,
            fibre_loading_wt_pct=args.fibre_loading,
            naoh_concentration_pct=args.naoh_conc,
            treatment_time_h=args.treatment_time,
            fibre_length_mm=args.fibre_length,
        )
        res = predict_property(
            inp,
            project_root=args.project_root,
            allow_demo_benchmark=args.demo_mode,
        )
        if res.is_ready and res.predicted_value is not None:
            if res.is_demo_benchmark:
                print("[DEMO BENCHMARK MODE - Software walkthrough only]")
            print(f"Predicted {res.target}: {res.predicted_value} {res.predicted_unit}")
            if res.lower_bound_95 is not None and res.upper_bound_95 is not None:
                print(f"95% Confidence Interval: [{res.lower_bound_95}, {res.upper_bound_95}] {res.predicted_unit}")
            else:
                print("95% Confidence Interval: Not available (Requires empirical model calibration on verified laboratory data)")
            if res.model_metrics:
                print(f"Evaluation Metrics: MAE={res.model_metrics.get('mae')}, RMSE={res.model_metrics.get('rmse')}, R2={res.model_metrics.get('r2')}")
            if res.validation_warnings:
                for w in res.validation_warnings:
                    print(f"Warning: {w}")
            return 0
        else:
            print(f"Prediction unavailable for target '{res.target}': Model Not Ready")
            for reason in res.reasons_unready:
                print(f"- {reason}")
            if res.validation_warnings:
                for w in res.validation_warnings:
                    print(f"Warning: {w}")
            return 1
    if args.command == "dashboard":
        import subprocess

        dashboard_file = Path(__file__).parents[2] / "dashboard" / "app.py"
        if not dashboard_file.is_file():
            print(f"Dashboard file not found: {dashboard_file}", file=sys.stderr)
            return 2
        print(f"Starting EcoFiber AI Streamlit dashboard on port {args.port}...")
        cmd = [sys.executable, "-m", "streamlit", "run", str(dashboard_file), "--server.port", str(args.port)]
        return subprocess.call(cmd)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line interface for single-object and relational bundle generation."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from .bundle import generate_bundle
from .config import apply_stage_overrides, deep_merge, validate_config
from .defaults import DEFAULT_CONFIG, PRESETS
from .generator import SalesforceGenerator, parse_columns
from .io import groq_enrich, write_records


BUNDLE_ONLY_FLAGS = ("--users", "--accounts", "--contacts", "--opportunities", "--overwrite")
BUNDLE_INCOMPATIBLE_FLAGS = (
    "--object", "--rows", "--columns", "--columns-file", "--output", "--format",
    "--list-presets", "--list-fields", "--write-example-config",
    "--groq-fields", "--groq-limit", "--groq-model", "--groq-api-key-env",
)


def _flag_present(arguments: list[str], flag: str) -> bool:
    return any(argument == flag or argument.startswith(flag + "=") for argument in arguments)


def _as_of_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must use YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate coherent synthetic Salesforce-style records or relational bundles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python salesforce_synthetic_data.py --object opportunity --rows 5000
  python salesforce_synthetic_data.py --object account --rows 15000 --regions EMEA,APAC
  python salesforce_synthetic_data.py --object opportunity --rows 2000 \\
    --columns 'Id,Name,StageName,Amount,CloseDate,IsClosed,IsWon,Sales Region,Sales District'
  sf-synthetic-data --bundle-dir output/sales_scenario --users 50 \\
    --accounts 2000 --contacts 5000 --opportunities 15000 --as-of-date 2026-01-01
""",
    )
    parser.add_argument("--object", choices=sorted(PRESETS), default="opportunity", help="Salesforce object preset (default: opportunity)")
    parser.add_argument("--rows", type=int, default=2000, help="Number of rows (default: 2000)")
    parser.add_argument("--columns", help="Comma, tab, semicolon, or newline-separated column list")
    parser.add_argument("--columns-file", type=Path, help="Text file containing pasted column names")
    parser.add_argument("--output", type=Path, help="Output path; defaults to synthetic_<object>_<rows>.csv")
    parser.add_argument("--format", choices=["csv", "jsonl"], help="Output format; inferred from extension when omitted")
    parser.add_argument("--seed", type=int, default=42, help="Repeatable random seed")
    parser.add_argument("--as-of-date", type=_as_of_date, help="Stable generation date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--config", type=Path, help="JSON file overriding regions, stages, and picklists")
    parser.add_argument("--regions", help="Comma-separated region names to include")
    parser.add_argument("--districts", help="Comma-separated district names to include")
    parser.add_argument("--stages", help="Comma-separated opportunity stage names")
    parser.add_argument("--won-rate", type=float, help="Target Closed Won share from 0 to 1")
    parser.add_argument("--lost-rate", type=float, help="Target Closed Lost share from 0 to 1")
    parser.add_argument("--list-presets", action="store_true", help="List available object presets")
    parser.add_argument("--list-fields", choices=sorted(PRESETS), help="Print preset fields for one object")
    parser.add_argument("--write-example-config", type=Path, help="Write a configurable JSON example and exit")
    parser.add_argument("--groq-fields", help="Optional comma-separated text fields to enrich using Groq")
    parser.add_argument("--groq-limit", type=int, default=100, help="Maximum rows sent to Groq (default: 100)")
    parser.add_argument("--groq-model", default="openai/gpt-oss-20b", help="Groq model ID")
    parser.add_argument("--groq-api-key-env", default="GROQ_API_KEY", help="Environment variable containing the Groq API key")
    parser.add_argument("--bundle-dir", type=Path, help="Create a relational Users/Accounts/Contacts/Opportunities CSV bundle")
    parser.add_argument("--users", type=int, help="Exact User count for bundle mode")
    parser.add_argument("--accounts", type=int, help="Exact Account count for bundle mode")
    parser.add_argument("--contacts", type=int, help="Exact Contact count for bundle mode; may be zero")
    parser.add_argument("--opportunities", type=int, help="Exact Opportunity count for bundle mode; may be zero")
    parser.add_argument("--overwrite", action="store_true", help="Replace generated files in a non-empty bundle directory")
    return parser


def _load_config(args: argparse.Namespace) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    if args.config:
        override = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(override, dict):
            raise ValueError("config file must contain a JSON object")
        config = deep_merge(config, override)
    stage_names = parse_columns(args.stages) if args.stages else None
    apply_stage_overrides(config, stage_names, args.won_rate, args.lost_rate)
    validate_config(config)
    return config


def _selected_filters(args: argparse.Namespace) -> tuple[set[str] | None, set[str] | None]:
    regions = set(parse_columns(args.regions)) if args.regions else None
    districts = set(parse_columns(args.districts)) if args.districts else None
    return regions, districts


def _run(arguments: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    as_of_date = args.as_of_date or date.today()

    if args.bundle_dir:
        incompatible = [flag for flag in BUNDLE_INCOMPATIBLE_FLAGS if _flag_present(arguments, flag)]
        if incompatible:
            raise ValueError(f"bundle mode does not support: {', '.join(incompatible)}")
        missing = [flag for flag in ("--users", "--accounts", "--contacts", "--opportunities") if not _flag_present(arguments, flag)]
        if missing:
            raise ValueError(f"bundle mode requires explicit counts: {', '.join(missing)}")
        config = _load_config(args)
        region_filter, district_filter = _selected_filters(args)
        counts = {
            "users": args.users,
            "accounts": args.accounts,
            "contacts": args.contacts,
            "opportunities": args.opportunities,
        }
        manifest = generate_bundle(
            args.bundle_dir, counts, config, args.seed, as_of_date,
            region_filter, district_filter, args.overwrite,
        )
        print(f"Generated relational bundle -> {args.bundle_dir}")
        print("Counts: " + ", ".join(f"{name}={details['count']:,}" for name, details in manifest["objects"].items()))
        return 0

    bundle_only = [flag for flag in BUNDLE_ONLY_FLAGS if _flag_present(arguments, flag)]
    if bundle_only:
        raise ValueError(f"{', '.join(bundle_only)} require --bundle-dir")
    if args.list_presets:
        for name in sorted(PRESETS):
            print(f"{name}: {len(PRESETS[name])} fields")
        return 0
    if args.list_fields:
        print("\n".join(PRESETS[args.list_fields]))
        return 0
    if args.write_example_config:
        args.write_example_config.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {args.write_example_config}")
        return 0

    config = _load_config(args)
    if args.columns and args.columns_file:
        raise ValueError("use either --columns or --columns-file, not both")
    if args.columns_file:
        columns = parse_columns(args.columns_file.read_text(encoding="utf-8"))
    elif args.columns:
        columns = parse_columns(args.columns)
    else:
        columns = PRESETS[args.object]
    region_filter, district_filter = _selected_filters(args)
    generator = SalesforceGenerator(
        args.object, args.rows, config, args.seed,
        region_filter, district_filter, as_of_date,
    )
    records = generator.generate(columns)
    if args.groq_fields:
        materialized = list(records)
        fields = parse_columns(args.groq_fields)
        missing = [field for field in fields if field not in columns]
        if missing:
            raise ValueError(f"Groq fields must also be output columns: {', '.join(missing)}")
        groq_enrich(materialized, fields, args.object, args.groq_model, args.groq_limit, args.groq_api_key_env)
        records = iter(materialized)

    output = args.output or Path(f"synthetic_{args.object}_{args.rows}.csv")
    output_format = args.format or ("jsonl" if output.suffix.lower() in {".jsonl", ".ndjson"} else "csv")
    count = write_records(records, columns, output, output_format)
    print(f"Generated {count:,} {args.object} rows -> {output}")
    print(f"Columns: {', '.join(columns)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(list(sys.argv[1:] if argv is None else argv))
    except (ValueError, OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

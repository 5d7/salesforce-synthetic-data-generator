"""Salesforce Synthetic Data Generator public API."""

from .bundle import GENERATOR_VERSION, generate_bundle
from .cli import build_parser, main
from .config import apply_stage_overrides, deep_merge, merged_config, validate_config
from .defaults import (
    ALIASES,
    COMPANY_NOUNS,
    COMPANY_WORDS,
    DEFAULT_CONFIG,
    DEPARTMENTS,
    FIRST_NAMES,
    ID_PREFIX,
    LAST_NAMES,
    LOCATION_BY_REGION,
    PRESETS,
    TITLES,
)
from .generator import (
    SalesforceGenerator,
    Stage,
    base36,
    canonical_field,
    iso_datetime,
    normalize,
    parse_columns,
    sf_id,
    slug,
    stable_seed,
    weighted_choice,
)
from .io import groq_enrich, write_records

__all__ = [
    "ALIASES", "COMPANY_NOUNS", "COMPANY_WORDS", "DEFAULT_CONFIG", "DEPARTMENTS",
    "FIRST_NAMES", "GENERATOR_VERSION", "ID_PREFIX", "LAST_NAMES", "LOCATION_BY_REGION",
    "PRESETS", "SalesforceGenerator", "Stage", "TITLES",
    "apply_stage_overrides", "base36", "build_parser", "canonical_field", "deep_merge",
    "generate_bundle", "groq_enrich", "iso_datetime", "main", "merged_config", "normalize",
    "parse_columns", "sf_id", "slug", "stable_seed", "validate_config", "weighted_choice",
    "write_records",
]

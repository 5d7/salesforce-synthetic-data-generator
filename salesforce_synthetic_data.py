#!/usr/bin/env python3
"""Backward-compatible module and executable entry point."""

from sf_synthetic_data import (  # noqa: F401
    ALIASES,
    COMPANY_NOUNS,
    COMPANY_WORDS,
    DEFAULT_CONFIG,
    DEPARTMENTS,
    FIRST_NAMES,
    GENERATOR_VERSION,
    ID_PREFIX,
    LAST_NAMES,
    LOCATION_BY_REGION,
    PRESETS,
    SalesforceGenerator,
    Stage,
    TITLES,
    apply_stage_overrides,
    base36,
    build_parser,
    canonical_field,
    deep_merge,
    generate_bundle,
    groq_enrich,
    iso_datetime,
    main,
    merged_config,
    normalize,
    parse_columns,
    sf_id,
    slug,
    stable_seed,
    validate_config,
    weighted_choice,
    write_records,
)


if __name__ == "__main__":
    raise SystemExit(main())

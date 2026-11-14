"""Configuration parsing and validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .defaults import DEFAULT_CONFIG


PICKLIST_KEYS = (
    "lead_statuses", "case_statuses", "industries", "account_types",
    "lead_sources", "opportunity_types", "case_types", "currencies",
)
STAGE_KEYS = {"name", "probability", "weight", "is_closed", "is_won", "forecast"}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def merged_config(override: dict[str, Any] | None = None) -> dict[str, Any]:
    config = deep_merge(DEFAULT_CONFIG, override or {})
    validate_config(config)
    return config


def _string_list(config: dict[str, Any], key: str) -> None:
    value = config.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"config '{key}' must be a non-empty list of strings")


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict):
        raise ValueError("config must be a JSON object")
    regions = config.get("regions")
    if not isinstance(regions, dict) or not regions:
        raise ValueError("config 'regions' must be a non-empty object")
    for region, districts in regions.items():
        if not isinstance(region, str) or not region.strip():
            raise ValueError("config region names must be non-empty strings")
        if not isinstance(districts, list) or not districts or not all(isinstance(item, str) and item.strip() for item in districts):
            raise ValueError(f"config region '{region}' must contain a non-empty list of districts")
        if len(set(districts)) != len(districts):
            raise ValueError(f"config region '{region}' contains duplicate districts")

    for key in PICKLIST_KEYS:
        _string_list(config, key)

    stages = config.get("opportunity_stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("config 'opportunity_stages' must be a non-empty list")
    positive_weight = False
    for index, stage in enumerate(stages, start=1):
        if not isinstance(stage, dict):
            raise ValueError(f"opportunity stage {index} must be an object")
        missing = STAGE_KEYS.difference(stage)
        if missing:
            raise ValueError(f"opportunity stage {index} is missing: {', '.join(sorted(missing))}")
        if not isinstance(stage["name"], str) or not stage["name"].strip():
            raise ValueError(f"opportunity stage {index} must have a non-empty name")
        if isinstance(stage["probability"], bool) or not isinstance(stage["probability"], (int, float)) or not 0 <= stage["probability"] <= 100:
            raise ValueError(f"opportunity stage '{stage['name']}' probability must be between 0 and 100")
        if isinstance(stage["weight"], bool) or not isinstance(stage["weight"], (int, float)) or stage["weight"] < 0:
            raise ValueError(f"opportunity stage '{stage['name']}' weight must be zero or greater")
        positive_weight = positive_weight or stage["weight"] > 0
        if not isinstance(stage["is_closed"], bool) or not isinstance(stage["is_won"], bool):
            raise ValueError(f"opportunity stage '{stage['name']}' closed/won flags must be booleans")
        if stage["is_won"] and not stage["is_closed"]:
            raise ValueError(f"opportunity stage '{stage['name']}' cannot be won without being closed")
        if not isinstance(stage["forecast"], str) or not stage["forecast"].strip():
            raise ValueError(f"opportunity stage '{stage['name']}' must have a forecast category")
    if not positive_weight:
        raise ValueError("opportunity_stages must contain at least one stage with a positive weight")


def validate_filters(
    config: dict[str, Any],
    region_filter: set[str] | None,
    district_filter: set[str] | None,
) -> dict[str, list[str]]:
    regions: dict[str, list[str]] = config["regions"]
    unknown_regions = sorted((region_filter or set()).difference(regions))
    if unknown_regions:
        raise ValueError(f"unknown region(s): {', '.join(unknown_regions)}")
    known_districts = {district for districts in regions.values() for district in districts}
    unknown_districts = sorted((district_filter or set()).difference(known_districts))
    if unknown_districts:
        raise ValueError(f"unknown district(s): {', '.join(unknown_districts)}")
    selected = {
        region: [district for district in districts if not district_filter or district in district_filter]
        for region, districts in regions.items()
        if not region_filter or region in region_filter
    }
    selected = {region: districts for region, districts in selected.items() if districts}
    if not selected:
        raise ValueError("the selected region/district filters produced no valid combinations")
    return selected


def apply_stage_overrides(
    config: dict[str, Any],
    names: list[str] | None,
    won_rate: float | None,
    lost_rate: float | None,
) -> None:
    if names:
        stages = []
        open_names = [name for name in names if "closed" not in name.lower()]
        for index, name in enumerate(names):
            lower = name.lower()
            is_won = "won" in lower
            is_closed = "closed" in lower or is_won or "lost" in lower
            probability = 100 if is_won else 0 if is_closed else round(10 + 80 * (index / max(1, len(open_names))))
            forecast = "Closed" if is_won else "Omitted" if is_closed else "Pipeline" if probability < 40 else "Best Case" if probability < 70 else "Commit"
            stages.append({"name": name, "probability": probability, "weight": 1, "is_closed": is_closed, "is_won": is_won, "forecast": forecast})
        config["opportunity_stages"] = stages
    if won_rate is not None or lost_rate is not None:
        won = 0.16 if won_rate is None else won_rate
        lost = 0.10 if lost_rate is None else lost_rate
        if not 0 <= won <= 1 or not 0 <= lost <= 1 or won + lost > 1:
            raise ValueError("won-rate and lost-rate must be between 0 and 1 and sum to at most 1")
        stages = config["opportunity_stages"]
        if won > 0 and not any(stage["is_won"] for stage in stages):
            raise ValueError("won-rate requires a Closed Won stage")
        if lost > 0 and not any(stage["is_closed"] and not stage["is_won"] for stage in stages):
            raise ValueError("lost-rate requires a Closed Lost stage")
        open_stages = [stage for stage in stages if not stage["is_closed"]]
        if 1 - won - lost > 0 and not open_stages:
            raise ValueError("won-rate and lost-rate leave open pipeline but no open stage exists")
        for stage in stages:
            if stage["is_won"]:
                stage["weight"] = won
            elif stage["is_closed"]:
                stage["weight"] = lost
            else:
                stage["weight"] = (1 - won - lost) / max(1, len(open_stages))
    validate_config(config)

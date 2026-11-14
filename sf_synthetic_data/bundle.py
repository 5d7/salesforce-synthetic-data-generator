"""Relational Sales Cloud bundle generation."""

from __future__ import annotations

import hashlib
import json
import os
import random
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .config import validate_config, validate_filters
from .defaults import PRESETS
from .generator import SalesforceGenerator, stable_seed
from .io import write_records


GENERATOR_VERSION = "0.2.0"
IMPORT_ORDER = ["users", "accounts", "contacts", "opportunities"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _config_sha256(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_counts(counts: dict[str, int]) -> None:
    for key in ("users", "accounts", "contacts", "opportunities"):
        value = counts.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"--{key} must be an integer")
        minimum = 1 if key in {"users", "accounts"} else 0
        if value < minimum:
            raise ValueError(f"--{key} must be at least {minimum}")


def _prepare_directory(directory: Path, overwrite: bool) -> None:
    if directory.exists() and not directory.is_dir():
        raise ValueError(f"bundle directory is not a directory: {directory}")
    if directory.exists() and any(directory.iterdir()) and not overwrite:
        raise ValueError(f"bundle directory is not empty: {directory}; use --overwrite to replace generated files")
    directory.mkdir(parents=True, exist_ok=True)


def _records_with_accounts(
    records: Iterable[dict[str, Any]],
    accounts: list[dict[str, Any]],
    seed: int,
    object_name: str,
) -> Iterable[dict[str, Any]]:
    account_order = list(accounts)
    random.Random(stable_seed(seed, "bundle", object_name, "accounts")).shuffle(account_order)
    for index, record in enumerate(records):
        account = account_order[index % len(account_order)]
        record["AccountId"] = account["Id"]
        record["OwnerId"] = account["OwnerId"]
        record["Sales_Region__c"] = account["Sales_Region__c"]
        record["Sales_District__c"] = account["Sales_District__c"]
        if object_name == "opportunity":
            offer = record["Name"].split(" - ", 1)[-1]
            record["Name"] = f"{account['Name']} - {offer}"
            record["Description"] = (
                "Synthetic opportunity record for testing. "
                f"Region: {account['Sales_Region__c']}; district: {account['Sales_District__c']}."
            )
        yield record


def generate_bundle(
    directory: Path,
    counts: dict[str, int],
    config: dict[str, Any],
    seed: int,
    as_of_date: date,
    region_filter: set[str] | None = None,
    district_filter: set[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Generate a deterministic four-object relational bundle and return its manifest."""
    _validate_counts(counts)
    validate_config(config)
    region_map = validate_filters(config, region_filter, district_filter)
    _prepare_directory(directory, overwrite)
    temporary_paths: list[Path] = []
    final_paths: dict[str, Path] = {}
    try:
        user_generator = SalesforceGenerator(
            "user", counts["users"], config, stable_seed(seed, "bundle", "user"),
            region_filter, district_filter, as_of_date, scale_reference_pools=False,
        )
        users = list(user_generator.generate(PRESETS["user"]))
        territories = [(region, district) for region, districts in region_map.items() for district in districts]
        territory_offset = stable_seed(seed, "bundle", "territory-offset") % len(territories)
        for index, user in enumerate(users):
            region, district = territories[(territory_offset + index) % len(territories)]
            user["Sales_Region__c"] = region
            user["Sales_District__c"] = district
            user["ManagerId"] = "" if index == 0 else users[index - 1]["Id"]

        users_by_district: dict[str, list[dict[str, Any]]] = defaultdict(list)
        users_by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for user in users:
            users_by_district[user["Sales_District__c"]].append(user)
            users_by_region[user["Sales_Region__c"]].append(user)

        account_generator = SalesforceGenerator(
            "account", counts["accounts"], config, stable_seed(seed, "bundle", "account"),
            region_filter, district_filter, as_of_date, scale_reference_pools=False,
        )
        accounts = list(account_generator.generate(PRESETS["account"]))
        for index, account in enumerate(accounts):
            candidates = (
                users_by_district.get(account["Sales_District__c"])
                or users_by_region.get(account["Sales_Region__c"])
                or users
            )
            account["OwnerId"] = candidates[index % len(candidates)]["Id"]

        contact_generator = SalesforceGenerator(
            "contact", max(1, counts["contacts"]), config, stable_seed(seed, "bundle", "contact"),
            region_filter, district_filter, as_of_date, scale_reference_pools=False,
        )
        contacts: Iterable[dict[str, Any]] = (
            _records_with_accounts(contact_generator.generate(PRESETS["contact"]), accounts, seed, "contact")
            if counts["contacts"]
            else []
        )
        if counts["contacts"]:
            contacts = (record for index, record in enumerate(contacts) if index < counts["contacts"])

        opportunity_generator = SalesforceGenerator(
            "opportunity", max(1, counts["opportunities"]), config, stable_seed(seed, "bundle", "opportunity"),
            region_filter, district_filter, as_of_date, scale_reference_pools=False,
        )
        opportunities: Iterable[dict[str, Any]] = (
            _records_with_accounts(opportunity_generator.generate(PRESETS["opportunity"]), accounts, seed, "opportunity")
            if counts["opportunities"]
            else []
        )
        if counts["opportunities"]:
            opportunities = (record for index, record in enumerate(opportunities) if index < counts["opportunities"])

        record_sets: dict[str, tuple[Iterable[dict[str, Any]], list[str]]] = {
            "users": (users, PRESETS["user"]),
            "accounts": (accounts, PRESETS["account"]),
            "contacts": (contacts, PRESETS["contact"]),
            "opportunities": (opportunities, PRESETS["opportunity"]),
        }
        objects: dict[str, Any] = {}
        for plural_name in IMPORT_ORDER:
            records, columns = record_sets[plural_name]
            final_path = directory / f"{plural_name}.csv"
            temporary_path = directory / f".{plural_name}.csv.tmp"
            temporary_paths.append(temporary_path)
            written = write_records(records, columns, temporary_path, "csv")
            os.replace(temporary_path, final_path)
            final_paths[plural_name] = final_path
            objects[plural_name] = {
                "file": final_path.name,
                "count": written,
                "id_field": "Id",
                "sha256": _sha256(final_path),
            }

        manifest = {
            "schema_version": "1.0",
            "generator_version": GENERATOR_VERSION,
            "seed": seed,
            "as_of_date": as_of_date.isoformat(),
            "config_sha256": _config_sha256(config),
            "filters": {
                "regions": sorted(region_filter) if region_filter else [],
                "districts": sorted(district_filter) if district_filter else [],
            },
            "import_order": IMPORT_ORDER,
            "objects": objects,
            "relationships": [
                {"from": "users.ManagerId", "to": "users.Id", "nullable": True},
                {"from": "accounts.OwnerId", "to": "users.Id"},
                {"from": "contacts.AccountId", "to": "accounts.Id"},
                {"from": "contacts.OwnerId", "to": "users.Id"},
                {"from": "opportunities.AccountId", "to": "accounts.Id"},
                {"from": "opportunities.OwnerId", "to": "users.Id"},
            ],
        }
        manifest_path = directory / "manifest.json"
        manifest_temporary_path = directory / ".manifest.json.tmp"
        temporary_paths.append(manifest_temporary_path)
        manifest_temporary_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(manifest_temporary_path, manifest_path)
        return manifest
    finally:
        for temporary_path in temporary_paths:
            temporary_path.unlink(missing_ok=True)

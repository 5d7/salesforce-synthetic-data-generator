import csv
import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

from salesforce_synthetic_data import DEFAULT_CONFIG, generate_bundle


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationalBundleTests(unittest.TestCase):
    def generate(self, directory: Path, **overrides):
        counts = {"users": 20, "accounts": 40, "contacts": 60, "opportunities": 80}
        counts.update(overrides.pop("counts", {}))
        return generate_bundle(
            directory,
            counts,
            deepcopy(DEFAULT_CONFIG),
            overrides.pop("seed", 42),
            date(2026, 1, 1),
            overwrite=overrides.pop("overwrite", False),
            **overrides,
        )

    def test_counts_relationships_and_territories_are_coherent(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            manifest = self.generate(directory)
            users = read_csv(directory / "users.csv")
            accounts = read_csv(directory / "accounts.csv")
            contacts = read_csv(directory / "contacts.csv")
            opportunities = read_csv(directory / "opportunities.csv")

            self.assertEqual([len(users), len(accounts), len(contacts), len(opportunities)], [20, 40, 60, 80])
            user_by_id = {row["Id"]: row for row in users}
            account_by_id = {row["Id"]: row for row in accounts}
            self.assertEqual(users[0]["ManagerId"], "")
            self.assertTrue(all(not row["ManagerId"] or row["ManagerId"] in user_by_id for row in users))
            for account in accounts:
                owner = user_by_id[account["OwnerId"]]
                self.assertEqual(owner["Sales_District__c"], account["Sales_District__c"])
                self.assertEqual(owner["Sales_Region__c"], account["Sales_Region__c"])
            for child in contacts + opportunities:
                account = account_by_id[child["AccountId"]]
                self.assertIn(child["OwnerId"], user_by_id)
                self.assertEqual(child["OwnerId"], account["OwnerId"])
                self.assertEqual(child["Sales_Region__c"], account["Sales_Region__c"])
                self.assertEqual(child["Sales_District__c"], account["Sales_District__c"])
            for opportunity in opportunities:
                self.assertTrue(opportunity["Name"].startswith(account_by_id[opportunity["AccountId"]]["Name"] + " - "))

            self.assertEqual(manifest["import_order"], ["users", "accounts", "contacts", "opportunities"])
            self.assertEqual(manifest["generator_version"], "0.2.0")
            for object_name, details in manifest["objects"].items():
                self.assertEqual(details["sha256"], sha256(directory / details["file"]), object_name)

    def test_same_inputs_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as first_temporary, tempfile.TemporaryDirectory() as second_temporary:
            first = Path(first_temporary)
            second = Path(second_temporary)
            self.generate(first)
            self.generate(second)
            for filename in ["users.csv", "accounts.csv", "contacts.csv", "opportunities.csv", "manifest.json"]:
                self.assertEqual((first / filename).read_bytes(), (second / filename).read_bytes(), filename)

    def test_different_seed_changes_data_but_keeps_links_valid(self):
        with tempfile.TemporaryDirectory() as first_temporary, tempfile.TemporaryDirectory() as second_temporary:
            first = Path(first_temporary)
            second = Path(second_temporary)
            self.generate(first, seed=1)
            self.generate(second, seed=2)
            self.assertNotEqual((first / "accounts.csv").read_bytes(), (second / "accounts.csv").read_bytes())
            user_ids = {row["Id"] for row in read_csv(second / "users.csv")}
            account_ids = {row["Id"] for row in read_csv(second / "accounts.csv")}
            self.assertTrue(all(row["OwnerId"] in user_ids for row in read_csv(second / "accounts.csv")))
            self.assertTrue(all(row["AccountId"] in account_ids for row in read_csv(second / "opportunities.csv")))

    def test_zero_optional_children_still_write_header_only_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            manifest = self.generate(directory, counts={"contacts": 0, "opportunities": 0})
            self.assertEqual(read_csv(directory / "contacts.csv"), [])
            self.assertEqual(read_csv(directory / "opportunities.csv"), [])
            self.assertEqual(manifest["objects"]["contacts"]["count"], 0)
            self.assertEqual(manifest["objects"]["opportunities"]["count"], 0)

    def test_non_empty_directory_is_protected_and_overwrite_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            (directory / "keep.txt").write_text("user file", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not empty"):
                self.generate(directory)
            self.generate(directory, overwrite=True)
            self.assertEqual((directory / "keep.txt").read_text(encoding="utf-8"), "user file")

    def test_invalid_counts_and_filters_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            with self.assertRaisesRegex(ValueError, "users"):
                self.generate(directory, counts={"users": 0})
            with self.assertRaisesRegex(ValueError, "unknown district"):
                self.generate(directory, district_filter={"Atlantis"})

    def test_manifest_is_valid_json_on_disk(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            returned = self.generate(directory)
            stored = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(returned, stored)

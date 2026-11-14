import csv
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

from salesforce_synthetic_data import (
    DEFAULT_CONFIG,
    PRESETS,
    SalesforceGenerator,
    apply_stage_overrides,
    canonical_field,
    deep_merge,
    parse_columns,
    sf_id,
    write_records,
    validate_config,
)


class SalesforceSyntheticDataTests(unittest.TestCase):
    def test_salesforce_ids_have_a_valid_18_character_checksum(self):
        value = sf_id("opportunity", 12345)
        self.assertEqual(len(value), 18)
        self.assertTrue(value.startswith("006"))
        self.assertEqual(value, sf_id("opportunity", 12345))

    def test_pasted_columns_accept_friendly_labels(self):
        columns = parse_columns("Id\nOpportunity Name\tStage\nClosed Won Amount\nSales District")
        self.assertEqual(len(columns), 5)
        self.assertEqual(canonical_field(columns[1]), "Name")
        self.assertEqual(canonical_field(columns[2]), "StageName")
        self.assertEqual(canonical_field(columns[3]), "Closed_Won_Amount__c")
        self.assertEqual(canonical_field(columns[4]), "Sales_District__c")

    def test_opportunity_stage_and_amount_fields_are_consistent(self):
        generator = SalesforceGenerator("opportunity", 500, DEFAULT_CONFIG, seed=9)
        columns = PRESETS["opportunity"]
        records = list(generator.generate(columns))

        self.assertEqual(len(records), 500)
        self.assertEqual(len({row["Id"] for row in records}), 500)
        for row in records:
            self.assertEqual(row["Closed_Won_Amount__c"], row["Amount"] if row["IsWon"] else 0.0)
            self.assertEqual(row["Open_Pipeline_Amount__c"], 0.0 if row["IsClosed"] else row["Amount"])
            if row["IsWon"]:
                self.assertTrue(row["IsClosed"])
                self.assertEqual(row["Probability"], 100)

    def test_region_and_district_filters_are_honoured(self):
        generator = SalesforceGenerator(
            "account", 100, DEFAULT_CONFIG, seed=4,
            region_filter={"EMEA"}, district_filter={"UKI", "DACH"},
        )
        records = list(generator.generate(["Sales_Region__c", "Sales_District__c"]))
        self.assertEqual({row["Sales_Region__c"] for row in records}, {"EMEA"})
        self.assertTrue({row["Sales_District__c"] for row in records} <= {"UKI", "DACH"})

    def test_won_and_lost_rate_overrides_are_valid(self):
        config = deep_merge(DEFAULT_CONFIG, {})
        apply_stage_overrides(config, None, won_rate=0.25, lost_rate=0.15)
        total = sum(stage["weight"] for stage in config["opportunity_stages"])
        self.assertAlmostEqual(total, 1.0)

    def test_csv_writer_outputs_requested_row_count(self):
        generator = SalesforceGenerator("lead", 25, DEFAULT_CONFIG, seed=1)
        columns = ["Id", "FirstName", "LastName", "Company", "Status"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "leads.csv"
            count = write_records(generator.generate(columns), columns, path, "csv")
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(count, 25)
        self.assertEqual(len(rows), 25)

    def test_seed_and_as_of_date_are_independent_of_column_order(self):
        first_columns = ["Id", "Name", "Amount", "StageName", "Custom Score"]
        second_columns = list(reversed(first_columns))
        first = list(SalesforceGenerator(
            "opportunity", 20, DEFAULT_CONFIG, seed=42, as_of_date=date(2026, 1, 1)
        ).generate(first_columns))
        second = list(SalesforceGenerator(
            "opportunity", 20, DEFAULT_CONFIG, seed=42, as_of_date=date(2026, 1, 1)
        ).generate(second_columns))
        for first_row, second_row in zip(first, second):
            for column in first_columns:
                self.assertEqual(first_row[column], second_row[column])

    def test_different_seeds_change_records(self):
        columns = ["Id", "Name", "Amount", "StageName"]
        first = list(SalesforceGenerator(
            "opportunity", 5, DEFAULT_CONFIG, seed=1, as_of_date=date(2026, 1, 1)
        ).generate(columns))
        second = list(SalesforceGenerator(
            "opportunity", 5, DEFAULT_CONFIG, seed=2, as_of_date=date(2026, 1, 1)
        ).generate(columns))
        self.assertNotEqual(first, second)

    def test_config_validation_has_actionable_errors(self):
        config = deepcopy(DEFAULT_CONFIG)
        config["opportunity_stages"] = [{"name": "Incomplete"}]
        with self.assertRaisesRegex(ValueError, "missing"):
            validate_config(config)

        config = deepcopy(DEFAULT_CONFIG)
        config["currencies"] = []
        with self.assertRaisesRegex(ValueError, "currencies"):
            validate_config(config)

    def test_unknown_filters_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown region"):
            SalesforceGenerator("account", 1, DEFAULT_CONFIG, seed=1, region_filter={"MARS"})


if __name__ == "__main__":
    unittest.main()

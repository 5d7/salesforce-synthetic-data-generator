import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from salesforce_synthetic_data import main


class CommandLineTests(unittest.TestCase):
    def run_cli(self, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_bundle_requires_every_explicit_count(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            result, _, error = self.run_cli([
                "--bundle-dir", temporary_directory,
                "--users", "2", "--accounts", "4", "--contacts", "5",
            ])
        self.assertEqual(result, 2)
        self.assertIn("--opportunities", error)

    def test_bundle_rejects_single_object_flags(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            result, _, error = self.run_cli([
                "--bundle-dir", temporary_directory,
                "--users", "2", "--accounts", "4", "--contacts", "5", "--opportunities", "6",
                "--rows", "10",
            ])
        self.assertEqual(result, 2)
        self.assertIn("--rows", error)

    def test_bundle_counts_require_bundle_directory(self):
        result, _, error = self.run_cli(["--users", "2"])
        self.assertEqual(result, 2)
        self.assertIn("require --bundle-dir", error)

    def test_single_object_cli_remains_available(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "accounts.csv"
            result, message, error = self.run_cli([
                "--object", "account", "--rows", "3", "--output", str(output),
                "--seed", "7", "--as-of-date", "2026-01-01",
            ])
            self.assertEqual(result, 0, error)
            self.assertIn("Generated 3 account rows", message)
            self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), 4)

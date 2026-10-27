"""Tests for the downloadable cleaning report."""

import unittest
from datetime import datetime

import pandas as pd

from backend.cleaning_report import build_cleaning_report
from backend.recommendations import CleaningChoices, clean_with_choices

WHEN = datetime(2026, 10, 26, 23, 5)


def messy_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-01", "2024-01-02", "not-a-date", "2024-01-04"],
            "amount": ["$1,000.00", "$1,000.00", None, "20", "30"],
            "category": ["Food", "Food", "Books", "Food", "Electonics"],
            "item": ["Coffee", "Coffee", "Novel", "Tea", "Pen"],
        }
    )


def report_for(choices: CleaningChoices, **kwargs) -> str:
    _, summary = clean_with_choices(messy_df(), choices)
    return build_cleaning_report(summary, generated_at=WHEN, **kwargs)


class CleaningReportTests(unittest.TestCase):
    def test_accepted_fixes_are_reported_with_counts(self) -> None:
        report = report_for(
            CleaningChoices(category_corrections={"Electonics": "Electronics"}),
            source_name="sales.csv",
        )

        self.assertIn("Generated: 2026-10-26 23:05", report)
        self.assertIn("File: sales.csv", report)
        self.assertIn("Rows before: 5", report)
        self.assertIn("Rows after: 4", report)
        self.assertIn("Rows removed: 1", report)
        self.assertIn("Duplicate rows: 1 found, 1 removed", report)
        self.assertIn("Missing amounts: 1 found, replaced with 0", report)
        self.assertIn("Invalid dates: 1 found, kept but excluded", report)
        self.assertIn("Amounts with $ or commas: 2 converted", report)
        self.assertIn("Electonics -> Electronics (1 row)", report)

    def test_rejected_fixes_are_reported_as_kept(self) -> None:
        report = report_for(
            CleaningChoices(remove_duplicates=False, fill_missing_amounts=False)
        )

        self.assertIn("Duplicate rows: 1 found, kept", report)
        self.assertIn("Missing amounts: 1 found, left empty", report)
        self.assertIn("Rows removed: 0", report)
        self.assertIn("Category spelling corrections: none applied", report)

    def test_removed_invalid_date_rows_are_reported(self) -> None:
        report = report_for(CleaningChoices(remove_invalid_date_rows=True))

        self.assertIn("Invalid dates: 1 found, rows removed", report)

    def test_clean_file_reports_none_found(self) -> None:
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "amount": [5],
                "category": ["Food"],
                "item": ["Tea"],
            }
        )
        _, summary = clean_with_choices(df, CleaningChoices())
        report = build_cleaning_report(summary, generated_at=WHEN)

        for phrase in (
            "Duplicate rows: none found",
            "Missing amounts: none found",
            "Invalid dates: none found",
            "Amounts with $ or commas: none found",
        ):
            self.assertIn(phrase, report)
        self.assertNotIn("File:", report)
        self.assertNotIn("Columns used", report)

    def test_column_mapping_is_included_when_used(self) -> None:
        report = report_for(
            CleaningChoices(),
            column_mapping={"date": "Transaction Date", "amount": "Revenue"},
        )

        self.assertIn("Columns used: Transaction Date -> date, Revenue -> amount", report)


if __name__ == "__main__":
    unittest.main()

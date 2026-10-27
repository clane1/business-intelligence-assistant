"""Headless end-to-end tests of the Streamlit workflow (no browser needed).

Each test seeds the session with a loaded file, as the upload step would, and
then drives the check, apply and dashboard steps through Streamlit's AppTest.
"""

import unittest
import warnings
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "frontend" / "streamlit_app_v2.py")
SALES = Path(__file__).resolve().parents[1] / "data" / "sales"


def open_check_page(csv_name: str) -> AppTest:
    """Start the app on the check page with a fixture already loaded."""
    df = pd.read_csv(SALES / csv_name)
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.session_state["raw_df"] = df
    at.session_state["source_df"] = df
    at.session_state["source_name"] = csv_name
    at.session_state["current_step"] = 2
    at.run()
    return at


def button(at: AppTest, prefix: str):
    matches = [b for b in at.button if b.label.startswith(prefix)]
    return matches[0] if matches else None


class AppFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        warnings.simplefilter("ignore")

    def test_messy_file_shows_recommendations_then_dashboard_and_report(self) -> None:
        at = open_check_page("sales_messy_1000.csv")
        self.assertFalse(at.exception)

        # Nothing is cleaned until the user applies fixes.
        self.assertIsNone(at.session_state["clean_df"])
        self.assertTrue(at.checkbox(key="fix_duplicates").value)
        self.assertTrue(at.checkbox(key="fix_missing_amounts").value)

        button(at, "Apply selected fixes").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 3)
        report = at.session_state["cleaning_report"]
        self.assertIn("Rows before: 1000", report)
        self.assertIn("Duplicate rows: 8 found, 8 removed", report)
        self.assertIn("sales_messy_1000.csv", report)

    def test_rejecting_duplicate_removal_is_respected(self) -> None:
        at = open_check_page("sales_messy_1000.csv")
        at.checkbox(key="fix_duplicates").uncheck()
        at.run()

        button(at, "Apply selected fixes").click()
        at.run()

        summary = at.session_state["cleaning_summary"]
        self.assertEqual(summary["duplicates_removed"], 0)
        self.assertIn("kept", at.session_state["cleaning_report"])

    def test_clean_file_offers_continue_instead_of_apply(self) -> None:
        at = open_check_page("sales_clean_100.csv")

        self.assertIsNone(button(at, "Apply selected fixes"))
        button(at, "Continue to dashboard").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 3)

    def test_misspelled_categories_are_offered_and_can_be_corrected(self) -> None:
        at = open_check_page("sales_misspelled_categories_20.csv")
        keys = [r.key for r in at.radio if str(r.key).startswith("fix_category_")]
        self.assertTrue(keys, "expected category suggestions")

        button(at, "Apply selected fixes").click()
        at.run()

        categories = set(at.session_state["clean_df"]["category"])
        self.assertNotIn("Electonics", categories)
        self.assertIn("Electronics", categories)

    def test_missing_column_blocks_cleaning(self) -> None:
        df = pd.read_csv(SALES / "sales_clean_100.csv").drop(columns=["item"])
        at = AppTest.from_file(APP, default_timeout=60)
        at.run()
        at.session_state["raw_df"] = df
        at.session_state["source_df"] = df
        at.session_state["current_step"] = 2
        at.run()

        self.assertTrue(any("item" in e.value for e in at.error))
        self.assertTrue(button(at, "Apply selected fixes").disabled)
        self.assertIsNotNone(button(at, "Back to Upload Data"))

    def test_non_numeric_amounts_block_cleaning_with_instructions(self) -> None:
        df = pd.read_csv(SALES / "sales_clean_100.csv")
        df["amount"] = df["amount"].astype(object)
        df.loc[0, "amount"] = "abc"
        at = AppTest.from_file(APP, default_timeout=60)
        at.run()
        at.session_state["raw_df"] = df
        at.session_state["source_df"] = df
        at.session_state["current_step"] = 2
        at.run()

        self.assertTrue(any("amount" in e.value for e in at.error))
        self.assertTrue(button(at, "Apply selected fixes").disabled)
        self.assertIsNotNone(button(at, "Back to Upload Data"))

    def test_start_new_analysis_resets_state(self) -> None:
        at = open_check_page("sales_messy_1000.csv")
        button(at, "Apply selected fixes").click()
        at.run()

        [b for b in at.sidebar.button if "Start New Analysis" in b.label][0].click()
        at.run()

        self.assertEqual(at.session_state["current_step"], 1)
        self.assertIsNone(at.session_state["raw_df"])
        self.assertIsNone(at.session_state["cleaning_report"])
        self.assertIsNone(at.session_state["source_name"])

    def test_dashboard_continues_to_insights(self) -> None:
        at = open_check_page("sales_sample_10.csv")
        button(at, "Continue to dashboard").click()
        at.run()
        button(at, "Continue to Insights").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 4)

    def test_every_valid_fixture_reaches_the_insights_page(self) -> None:
        for path in sorted(SALES.glob("*.csv")):
            if path.name.startswith(("sales_no_headers_", "sales_custom_headers_")):
                continue
            with self.subTest(fixture=path.name):
                at = open_check_page(path.name)
                if at.error:
                    continue  # blocked by design; covered by loader tests
                gate = button(at, "Apply selected fixes") or button(
                    at, "Continue to dashboard"
                )
                gate.click()
                at.run()
                button(at, "Continue to Insights").click()
                at.run()
                self.assertFalse(at.exception, at.exception)
                self.assertEqual(at.session_state["current_step"], 4)


if __name__ == "__main__":
    unittest.main()

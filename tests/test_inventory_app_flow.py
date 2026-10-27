"""Headless end-to-end tests of the Inventory workflow (no browser needed).

Like test_app_flow.py, each test seeds the session as the upload step would
and drives the later steps through Streamlit's AppTest.
"""

import unittest
import warnings
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from frontend.inventory_pages import REMOVE_NEGATIVES

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "frontend" / "streamlit_app_v2.py")
INVENTORY = ROOT / "data" / "inventory"


def open_check_page(csv_name: str) -> AppTest:
    """Start the app on the Inventory check page with a fixture loaded."""
    df = pd.read_csv(INVENTORY / csv_name)
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.session_state["dataset_type"] = "Inventory"
    at.session_state["raw_df"] = df
    at.session_state["source_df"] = df
    at.session_state["source_name"] = csv_name
    at.session_state["current_step"] = 2
    at.run()
    return at


def button(at: AppTest, prefix: str):
    matches = [b for b in at.button if b.label.startswith(prefix)]
    return matches[0] if matches else None


class InventoryAppFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        warnings.simplefilter("ignore")

    def test_messy_file_shows_cards_then_dashboard_and_report(self) -> None:
        at = open_check_page("inventory_messy_20.csv")
        self.assertFalse(at.exception)
        self.assertIsNone(at.session_state["clean_df"])
        self.assertTrue(at.checkbox(key="inv_fix_duplicates").value)
        self.assertTrue(at.checkbox(key="inv_fix_missing_quantity").value)

        button(at, "Apply selected fixes").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 3)
        report = at.session_state["cleaning_report"]
        self.assertIn("Inventory Cleaning Report", report)
        self.assertIn("Duplicate rows: 2 found, 2 removed", report)
        self.assertIn("Negative quantities: 1 found, kept for your review", report)

    def test_rejecting_duplicate_removal_is_respected(self) -> None:
        at = open_check_page("inventory_messy_20.csv")
        at.checkbox(key="inv_fix_duplicates").uncheck()
        at.run()

        button(at, "Apply selected fixes").click()
        at.run()

        self.assertEqual(at.session_state["cleaning_summary"]["duplicates_removed"], 0)

    def test_removing_negative_rows_is_respected(self) -> None:
        at = open_check_page("inventory_messy_20.csv")
        at.radio(key="inv_negative_quantity").set_value(REMOVE_NEGATIVES)
        at.run()

        button(at, "Apply selected fixes").click()
        at.run()

        self.assertEqual(at.session_state["cleaning_summary"]["negative_rows_removed"], 1)
        self.assertEqual((at.session_state["clean_df"]["quantity"] < 0).sum(), 0)

    def test_category_correction_can_be_accepted(self) -> None:
        at = open_check_page("inventory_messy_20.csv")
        keys = [r.key for r in at.radio if str(r.key).startswith("fix_category_")]
        self.assertEqual(len(keys), 3)

        button(at, "Apply selected fixes").click()
        at.run()

        categories = set(at.session_state["clean_df"]["category"])
        self.assertNotIn("Electonics", categories)

    def test_dashboard_and_insights_render_for_cleaned_data(self) -> None:
        at = open_check_page("inventory_messy_20.csv")
        button(at, "Apply selected fixes").click()
        at.run()

        self.assertFalse(at.exception)
        button(at, "Continue to Insights").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 4)

    def test_clean_file_offers_continue_instead_of_apply(self) -> None:
        at = open_check_page("inventory_clean_20.csv")

        self.assertIsNone(button(at, "Apply selected fixes"))
        button(at, "Continue to dashboard").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 3)

    def test_minimal_file_without_reorder_level_works(self) -> None:
        at = open_check_page("inventory_minimal_8.csv")
        button(at, "Continue to dashboard").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertIn(
            "not checked", at.session_state["cleaning_report"]
        )

    def test_zero_value_file_does_not_crash(self) -> None:
        at = open_check_page("inventory_zero_value_6.csv")
        buttons = [b for b in at.button if b.label.startswith(("Apply", "Continue to dashboard"))]
        buttons[0].click()
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 3)

    def test_non_numeric_file_blocks_cleaning(self) -> None:
        at = open_check_page("inventory_non_numeric_5.csv")

        self.assertFalse(at.exception)
        self.assertIsNotNone(button(at, "Back to Upload Data"))
        apply_buttons = [b for b in at.button if b.label.startswith("Apply")]
        self.assertTrue(all(b.disabled for b in apply_buttons))
        self.assertIsNone(at.session_state["clean_df"])

    def test_missing_required_column_blocks_with_back_button(self) -> None:
        at = open_check_page("inventory_missing_column_5.csv")

        self.assertFalse(at.exception)
        self.assertIsNotNone(button(at, "Back to Upload Data"))
        self.assertIsNone(at.session_state["clean_df"])

    def test_switching_dataset_type_resets_to_upload(self) -> None:
        at = open_check_page("inventory_messy_20.csv")

        at.session_state["current_step"] = 1
        at.run()
        at.selectbox(key="dataset_type_choice").set_value("Sales")
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["dataset_type"], "Sales")
        self.assertEqual(at.session_state["current_step"], 1)
        self.assertIsNone(at.session_state["raw_df"])

    def test_sales_is_the_default_dataset_type(self) -> None:
        at = AppTest.from_file(APP, default_timeout=60)
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["dataset_type"], "Sales")
        self.assertEqual(at.selectbox(key="dataset_type_choice").value, "Sales")


if __name__ == "__main__":
    unittest.main()

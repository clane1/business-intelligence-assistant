"""Headless end-to-end coverage for the Expenses Streamlit workflow."""

import unittest
import warnings
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "frontend" / "streamlit_app_v2.py")
EXPENSES = ROOT / "data" / "expenses"


def open_expenses_upload() -> AppTest:
    """Start the application on the Expenses upload page."""
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.selectbox(key="dataset_type_choice").set_value("Expenses")
    at.run()
    return at


def upload_fixture(at: AppTest, name: str) -> AppTest:
    """Upload a checked-in Expenses CSV through Streamlit's file uploader."""
    at.file_uploader(key="upload_Expenses").upload(
        name,
        (EXPENSES / name).read_bytes(),
        "text/csv",
    )
    at.run()
    return at


def button(at: AppTest, prefix: str):
    """Return the first button whose label starts with ``prefix``."""
    return next((element for element in at.button if element.label.startswith(prefix)), None)


class ExpensesAppFlowTests(unittest.TestCase):
    """Exercise user-visible upload, mapping, review, and analysis steps."""

    @classmethod
    def setUpClass(cls) -> None:
        warnings.simplefilter("ignore")

    def test_expenses_upload_reaches_dashboard_and_insights(self) -> None:
        at = open_expenses_upload()
        self.assertFalse(at.exception)
        upload_fixture(at, "expenses_clean_100.csv")

        self.assertIsNotNone(button(at, "Continue to data checks"))
        button(at, "Continue to data checks").click()
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 2)

        button(at, "Continue to dashboard").click()
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 3)
        self.assertEqual(
            list(at.session_state["clean_df"].columns),
            ["date", "amount", "category", "vendor"],
        )
        self.assertIn("Expenses Cleaning Report", at.session_state["cleaning_report"])
        metrics = {metric.label: metric.value for metric in at.metric}
        self.assertEqual(metrics["Total expenses"], "$26,762.50")
        self.assertEqual(metrics["Average expense"], "$267.62")
        self.assertEqual(metrics["Expense records"], "100")
        self.assertEqual(metrics["Largest expense category"], "Utilities")
        dashboard_headers = {header.value for header in at.header}
        self.assertTrue(
            {
                "Expenses by Category",
                "Expense Trend",
                "Percent of Spending by Category",
                "Expenses by Vendor",
            }.issubset(dashboard_headers)
        )
        button(at, "Continue to Insights").click()
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 4)
        self.assertTrue(any("largest spending source" in element.value for element in at.success))

    def test_expenses_custom_headers_can_be_mapped(self) -> None:
        at = upload_fixture(
            open_expenses_upload(),
            "expenses_custom_headers.csv",
        )
        button(at, "Continue to data checks").click()
        at.run()

        self.assertEqual(at.selectbox(key="map_date").value, "Transaction Date")
        self.assertEqual(at.selectbox(key="map_vendor").value, "Supplier")
        button(at, "Use these columns").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(
            list(at.session_state["raw_df"].columns),
            ["date", "amount", "category", "vendor"],
        )

    def test_non_numeric_amount_blocks_expense_cleaning(self) -> None:
        at = upload_fixture(open_expenses_upload(), "expenses_invalid_amount.csv")
        button(at, "Continue to data checks").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertIsNotNone(button(at, "Back to Upload Data"))
        self.assertTrue(
            all(
                element.disabled
                for element in at.button
                if element.label.startswith("Apply selected fixes")
            )
        )
        self.assertIsNone(at.session_state["clean_df"])

    def test_missing_vendor_is_reported_as_a_required_column(self) -> None:
        at = upload_fixture(open_expenses_upload(), "expenses_missing_column.csv")
        button(at, "Continue to data checks").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertTrue(any("vendor" in error.value for error in at.error))
        self.assertIsNotNone(button(at, "Back to Upload Data"))

    def test_dataset_switch_clears_expense_upload_state(self) -> None:
        at = upload_fixture(open_expenses_upload(), "expenses_clean_100.csv")
        self.assertIsNotNone(at.session_state["raw_df"])
        self.assertIn("upload_Expenses", at.session_state)

        at.selectbox(key="dataset_type_choice").set_value("Inventory")
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["dataset_type"], "Inventory")
        self.assertEqual(at.session_state["current_step"], 1)
        self.assertIsNone(at.session_state["raw_df"])
        self.assertIsNone(at.session_state["clean_df"])
        self.assertNotIn("upload_Expenses", at.session_state)

    def test_start_new_analysis_clears_expense_upload(self) -> None:
        at = upload_fixture(open_expenses_upload(), "expenses_clean_100.csv")
        self.assertIn("upload_Expenses", at.session_state)

        button(at, "🔄 Start New Analysis").click()
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_step"], 1)
        self.assertIsNone(at.session_state["raw_df"])
        self.assertIsNone(at.session_state["upload_Expenses"])
        self.assertIsNone(button(at, "Continue to data checks"))


if __name__ == "__main__":
    unittest.main()
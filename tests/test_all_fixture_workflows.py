"""Exercise every bundled CSV through the guided Streamlit upload workflow."""

import unittest
import warnings
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "frontend" / "streamlit_app_v2.py")
DATA = ROOT / "data"

BLOCKED_AT_UPLOAD = {"sales_no_headers_missing_column_2.csv": "four"}
BLOCKED_AT_CHECK = {
    "sales_missing_amount_2.csv": "amount",
    "inventory_missing_column_5.csv": "unit_cost",
    "inventory_non_numeric_5.csv": "quantity",
    "expenses_missing_column.csv": "vendor",
    "expenses_invalid_amount.csv": "amount",
}
CUSTOM_HEADERS = {
    "sales_custom_headers_8.csv",
    "inventory_custom_headers_6.csv",
    "expenses_custom_headers.csv",
}


def button(app: AppTest, prefix: str):
    return next((element for element in app.button if element.label.startswith(prefix)), None)


class FixtureWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        warnings.simplefilter("ignore")

    def test_every_bundled_dataset_from_upload_to_results(self) -> None:
        fixture_count = 0
        for dataset in ("Sales", "Inventory", "Expenses"):
            for path in sorted((DATA / dataset.lower()).glob("*.csv")):
                fixture_count += 1
                with self.subTest(dataset=dataset, fixture=path.name):
                    app = AppTest.from_file(APP, default_timeout=60).run()
                    if dataset != "Sales":
                        app.selectbox(key="dataset_type_choice").set_value(dataset)
                        app.run()
                    if "no_headers" in path.name:
                        app.checkbox[0].uncheck()
                        app.run()
                    if "semicolon" in path.name:
                        next(
                            select for select in app.selectbox
                            if select.label == "What separates the columns?"
                        ).set_value("Semicolon")
                        app.run()
                    app.file_uploader(key=f"upload_{dataset}").upload(
                        path.name, path.read_bytes(), "text/csv"
                    )
                    app.run()
                    self.assertFalse(app.exception, app.exception)

                    if path.name in BLOCKED_AT_UPLOAD:
                        self.assertTrue(app.error)
                        self.assertTrue(any(
                            BLOCKED_AT_UPLOAD[path.name] in error.value
                            for error in app.error
                        ))
                        self.assertIsNone(button(app, "Continue to data checks"))
                        continue

                    self.assertIsNotNone(button(app, "Continue to data checks"))
                    button(app, "Continue to data checks").click()
                    app.run()
                    self.assertFalse(app.exception, app.exception)
                    self.assertEqual(app.session_state["current_step"], 2)

                    if path.name in CUSTOM_HEADERS:
                        self.assertIsNotNone(button(app, "Use these columns"))
                        button(app, "Use these columns").click()
                        app.run()
                        self.assertFalse(app.exception, app.exception)

                    if path.name in BLOCKED_AT_CHECK:
                        self.assertTrue(
                            any(BLOCKED_AT_CHECK[path.name] in error.value for error in app.error),
                            [error.value for error in app.error],
                        )
                        self.assertIsNotNone(button(app, "Back to Upload Data"))
                        self.assertIsNone(app.session_state["clean_df"])
                        gate = button(app, "Apply selected fixes") or button(app, "Continue to dashboard")
                        self.assertTrue(gate is None or gate.disabled)
                        continue

                    self.assertFalse(app.error, [error.value for error in app.error])
                    gate = button(app, "Apply selected fixes") or button(app, "Continue to dashboard")
                    self.assertIsNotNone(gate)
                    self.assertFalse(gate.disabled)
                    gate.click()
                    app.run()
                    self.assertFalse(app.exception, app.exception)
                    self.assertEqual(app.session_state["current_step"], 3)
                    self.assertIsNotNone(app.session_state["cleaning_report"])
                    self.assertIsNotNone(app.session_state["clean_df"])
                    self.assertTrue(app.metric)
                    headers = {header.value for header in app.header}
                    self.assertEqual("Forecast" in headers, dataset == "Sales")
                    self.assertTrue(any("Download Cleaned CSV" in x.label for x in app.get("download_button")))
                    self.assertIsNotNone(button(app, "Continue to Insights"))
                    button(app, "Continue to Insights").click()
                    app.run()
                    self.assertFalse(app.exception, app.exception)
                    self.assertEqual(app.session_state["current_step"], 4)
                    self.assertTrue(app.success)
                    self.assertTrue(any("highlights" in x.label for x in app.get("download_button")))
        self.assertGreaterEqual(fixture_count, 41)

    def test_nonfinite_values_are_blocked_with_instructions(self) -> None:
        cases = [
            ("Sales", "date,amount,category,item\n2024-01-01,inf,Food,A\n", "amount"),
            ("Expenses", "date,amount,category,vendor\n2024-01-01,-inf,Food,A\n", "amount"),
            ("Inventory", "item,category,quantity,unit_cost\nA,Food,inf,2\n", "quantity"),
            ("Inventory", "item,category,quantity,unit_cost\nA,Food,1,-inf\n", "unit_cost"),
        ]
        for dataset, content, field in cases:
            with self.subTest(dataset=dataset, field=field):
                app = AppTest.from_file(APP, default_timeout=60).run()
                if dataset != "Sales":
                    app.selectbox(key="dataset_type_choice").set_value(dataset)
                    app.run()
                app.file_uploader(key=f"upload_{dataset}").upload(
                    "nonfinite.csv", content.encode(), "text/csv"
                )
                app.run()
                button(app, "Continue to data checks").click()
                app.run()
                self.assertFalse(app.exception, app.exception)
                self.assertTrue(
                    any(field in error.value for error in app.error),
                    [error.value for error in app.error],
                )
                self.assertIsNotNone(button(app, "Back to Upload Data"))
                self.assertIsNone(app.session_state["clean_df"])
                gate = button(app, "Apply selected fixes") or button(app, "Continue to dashboard")
                self.assertTrue(gate is None or gate.disabled)

    def test_nonfinite_optional_reorder_levels_are_excluded(self) -> None:
        content = (
            "item,category,quantity,unit_cost,reorder_level\n"
            "A,Food,1,2,inf\nB,Food,1,2,2\n"
        )
        app = AppTest.from_file(APP, default_timeout=60).run()
        app.selectbox(key="dataset_type_choice").set_value("Inventory")
        app.run()
        app.file_uploader(key="upload_Inventory").upload(
            "reorder.csv", content.encode(), "text/csv"
        )
        app.run()
        button(app, "Continue to data checks").click()
        app.run()
        self.assertFalse(app.exception, app.exception)
        self.assertTrue(any("reorder level" in item.value and "ignored" in item.value for item in app.info))
        gate = button(app, "Apply selected fixes") or button(app, "Continue to dashboard")
        gate.click()
        app.run()
        self.assertFalse(app.exception, app.exception)
        clean = app.session_state["clean_df"]
        self.assertTrue(clean.loc[clean["item"] == "A", "reorder_level"].isna().all())
        self.assertEqual(app.session_state["cleaning_summary"]["low_stock_items"], 1)

    def test_original_app_blocks_nonfinite_sales_amount(self) -> None:
        app = AppTest.from_file(str(ROOT / "frontend" / "streamlit_app.py"), default_timeout=60).run()
        app.file_uploader[0].upload(
            "nonfinite.csv", b"date,amount,category,item\n2024-01-01,inf,Food,A\n", "text/csv"
        )
        app.run()
        self.assertFalse(app.exception, app.exception)
        self.assertTrue(any("finite numbers" in error.value for error in app.error))
        self.assertFalse(any(header.value == "Forecast" for header in app.header))


if __name__ == "__main__":
    unittest.main()

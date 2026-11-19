"""Verify guidance when a CSV is uploaded under another dataset type."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "frontend" / "streamlit_app_v2.py")
FIXTURES = {
    "Sales": ROOT / "data" / "sales" / "sales_clean_100.csv",
    "Inventory": ROOT / "data" / "inventory" / "inventory_clean_20.csv",
    "Expenses": ROOT / "data" / "expenses" / "expenses_clean_100.csv",
}


def button(app: AppTest, prefix: str):
    return next((element for element in app.button if element.label.startswith(prefix)), None)


class DatasetMismatchTests(unittest.TestCase):
    def test_all_mismatched_schemas_show_guidance_without_blocking_mapping(self) -> None:
        for selected in FIXTURES:
            for actual, fixture in FIXTURES.items():
                if selected == actual:
                    continue
                with self.subTest(selected=selected, actual=actual):
                    app = AppTest.from_file(APP, default_timeout=60).run()
                    if selected != "Sales":
                        app.selectbox(key="dataset_type_choice").set_value(selected)
                        app.run()
                    app.file_uploader(key=f"upload_{selected}").upload(
                        fixture.name, fixture.read_bytes(), "text/csv"
                    )
                    app.run()
                    self.assertFalse(app.exception, app.exception)
                    self.assertTrue(any(
                        f"You selected {selected}" in warning.value
                        and f"match {actual}" in warning.value
                        and "choose the file again" in warning.value
                        for warning in app.warning
                    ))
                    button(app, "Continue to data checks").click()
                    app.run()
                    self.assertFalse(app.exception, app.exception)
                    self.assertTrue(any(f"match {actual}" in item.value for item in app.warning))
                    self.assertIsNotNone(button(app, "Use these columns"))
                    self.assertIsNone(app.session_state["clean_df"])

                    button(app, "Back to Upload Data").click()
                    app.run()
                    app.selectbox(key="dataset_type_choice").set_value(actual)
                    app.run()
                    self.assertEqual(app.session_state["dataset_type"], actual)
                    self.assertIsNone(app.session_state["raw_df"])
                    uploader = app.file_uploader[0]
                    uploader.upload(fixture.name, fixture.read_bytes(), "text/csv")
                    app.run()
                    self.assertFalse(app.exception, app.exception)
                    self.assertFalse(any("You selected" in item.value for item in app.warning))
                    self.assertIsNotNone(button(app, "Continue to data checks"))

    def test_headerless_upload_explains_detection_limit(self) -> None:
        for dataset in FIXTURES:
            with self.subTest(dataset=dataset):
                app = AppTest.from_file(APP, default_timeout=60).run()
                if dataset != "Sales":
                    app.selectbox(key="dataset_type_choice").set_value(dataset)
                    app.run()
                app.checkbox[0].uncheck()
                app.run()
                self.assertTrue(any(
                    "cannot determine the dataset type without column names" in item.value
                    for item in app.info
                ))

    def test_warning_does_not_prevent_explicit_custom_mapping(self) -> None:
        fixture = FIXTURES["Expenses"]
        app = AppTest.from_file(APP, default_timeout=60).run()
        app.file_uploader(key="upload_Sales").upload(
            fixture.name, fixture.read_bytes(), "text/csv"
        )
        app.run()
        button(app, "Continue to data checks").click()
        app.run()
        app.selectbox(key="map_item").set_value("vendor")
        app.run()
        button(app, "Use these columns").click()
        app.run()
        self.assertFalse(app.exception, app.exception)
        self.assertEqual(list(app.session_state["raw_df"].columns), [
            "date", "amount", "category", "item",
        ])
        self.assertIsNotNone(button(app, "Continue to dashboard"))


if __name__ == "__main__":
    unittest.main()

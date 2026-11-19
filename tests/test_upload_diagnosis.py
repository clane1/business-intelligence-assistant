"""Tests for upload error handling and setting diagnosis."""

import io
import unittest

import pandas as pd

from backend.csv_loader import SalesCsvFormatError, load_sales_csv
from backend.upload_diagnosis import detect_dataset_mismatch, diagnose_upload


def load(data: bytes, delimiter: str = ",", headers: bool = True) -> pd.DataFrame:
    return load_sales_csv(
        io.BytesIO(data), delimiter=delimiter, headers_included=headers
    )


class LoaderErrorTests(unittest.TestCase):
    def test_empty_file_gives_friendly_error(self) -> None:
        with self.assertRaisesRegex(SalesCsvFormatError, "file is empty"):
            load(b"")

    def test_non_text_file_gives_friendly_error(self) -> None:
        with self.assertRaisesRegex(SalesCsvFormatError, "can't be read as text"):
            load(bytes([0xFF, 0xFE, 0x00, 0x81, 0x82]) * 20)

    def test_unparseable_rows_give_friendly_error(self) -> None:
        with self.assertRaisesRegex(SalesCsvFormatError, "couldn't be read as a table"):
            load(b'a,b,c\n1,2,3\n"unclosed,2,3\n4,5,6,7,8\n', headers=True)


class DiagnosisTests(unittest.TestCase):
    def test_dataset_mismatch_only_for_unambiguous_standard_schemas(self) -> None:
        schemas = {
            "Sales": ["date", "amount", "category", "item"],
            "Expenses": ["date", "amount", "category", "vendor"],
            "Inventory": ["item", "category", "quantity", "unit_cost"],
        }
        for selected in schemas:
            for actual, columns in schemas.items():
                with self.subTest(selected=selected, actual=actual):
                    df = pd.DataFrame(columns=[f" {name.upper()} " for name in columns])
                    self.assertEqual(
                        detect_dataset_mismatch(df, selected),
                        actual if actual != selected else None,
                    )
        self.assertIsNone(detect_dataset_mismatch(
            pd.DataFrame(columns=["date", "amount", "category", "item", "vendor"]),
            "Sales",
        ))
        self.assertIsNone(detect_dataset_mismatch(
            pd.DataFrame(columns=["date", "amount", "category", "item", "vendor", "quantity", "unit_cost"]),
            "Inventory",
        ))
        self.assertIsNone(detect_dataset_mismatch(
            pd.DataFrame(columns=["Transaction Date", "Revenue", "Department", "Product"]),
            "Sales",
        ))

    def test_valid_file_has_no_problem(self) -> None:
        df = load(b"date,amount,category,item\n2024-01-01,5,Food,Tea\n")
        self.assertIsNone(diagnose_upload(df, ",", True))

    def test_header_only_file_is_reported(self) -> None:
        df = load(b"date,amount,category,item\n")
        self.assertIn("no data rows", diagnose_upload(df, ",", True))

    def test_wrong_delimiter_names_the_right_one(self) -> None:
        df = load(b"date;amount;category;item\n2024-01-01;5;Food;Tea\n")
        message = diagnose_upload(df, ",", True)
        self.assertIn("**Semicolon**", message)
        self.assertIn("choose your file again", message)

    def test_tab_file_read_as_comma_is_detected(self) -> None:
        df = load(b"date\tamount\tcategory\titem\n2024-01-01\t5\tFood\tTea\n")
        self.assertIn("**Tab**", diagnose_upload(df, ",", True))

    def test_first_row_data_treated_as_header_is_detected(self) -> None:
        df = load(b"2024-01-01,5,Food,Tea\n2024-01-02,6,Food,Tea\n")
        self.assertIn("first row looks like sales data", diagnose_upload(df, ",", True))

    def test_headerless_mode_not_flagged_for_data_first_row(self) -> None:
        df = load(b"2024-01-01,5,Food,Tea\n", headers=False)
        self.assertIsNone(diagnose_upload(df, ",", False))

    def test_real_fixtures_are_not_flagged(self) -> None:
        for name in ("sales_sample_10", "sales_messy_1000", "sales_custom_headers_8"):
            with self.subTest(name):
                df = pd.read_csv(f"data/sales/{name}.csv")
                self.assertIsNone(diagnose_upload(df, ",", True))


if __name__ == "__main__":
    unittest.main()

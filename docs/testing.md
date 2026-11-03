# Testing Sales, Inventory, and Expenses

## Automated regression tests

From the repository root, run the whole automated suite (the print-based
`test_pipeline.py` is excluded because it is a smoke script, not a test):

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_[a-oq-z]*.py"
```

Add `-v` for one line per test. Run a single file with, for example,
`.\venv\Scripts\python.exe -m unittest tests.test_recommendations`. Tests must
be run from the repository root because fixtures use relative paths.

| Test file | What it covers |
|---|---|
| `test_sales_trend.py` | Loader and delimiter/header handling, date parsing, trend granularity and chart labels, insight wording, and every CSV in `data/sales/`. |
| `test_validation_cleaning.py` | Each validation check and cleaning step on small inputs: missing columns, blocking vs. fixable amounts, supported date formats, duplicates, category normalization. |
| `test_recommendations.py` | Recommendation cards (counts, previews, examples), category spelling suggestions, and accept/reject behavior in `clean_with_choices`. |
| `test_column_mapping.py` | Suggested and applied column mappings for custom headers. |
| `test_upload_diagnosis.py` | Friendly loader errors and upload diagnosis (wrong delimiter, header-only file, header setting mismatch). |
| `test_cleaning_report.py` | Contents of the downloadable cleaning report. |
| `test_transformation.py` | KPIs, category and date aggregation, zero-revenue handling, and generated insights. |
| `test_app_flow.py` | Headless end-to-end workflow through the Streamlit app (check page, apply fixes, dashboard, report, reset, blocked files, every fixture reaching Insights). |
| `test_inventory.py` | Inventory validation, recommendation cards, accept/reject cleaning, KPIs, charts data, insights, low-stock logic, report, loader, mapping, the 100-row fixtures, and each issue-specific fixture in `data/inventory/`. |
| `test_inventory_app_flow.py` | Headless Inventory workflow: actual CSV upload, custom-header mapping, cards, accept/reject, negative-row removal, dashboard, insights, blocked files, and the dataset type switch resetting state. |
| `test_expenses.py` | Expenses CSV loading, custom-header mapping, validation, cleaning choices, reports, KPIs, category/vendor/date analysis, insights, date-only preview formatting, and all fixture scenarios. |
| `test_expenses_app_flow.py` | Headless Expenses upload, custom-header mapping, cleaning, dashboard, insights, blocked inputs, and dataset switching. |

`test_sales_trend.py` in detail: it verifies date parsing, trend interval
boundaries, explicit

chronological labels for daily, weekly, and monthly charts, and analysis
behavior across every standard CSV in `data/sales/`. It tests headerless
loading with comma- and semicolon-delimited fixtures, including a messy file,
and checks that a headerless file with the wrong column count is rejected with
an explicit explanation that the missing named field cannot be identified
without headers. It also checks the generic CSV parser, tab delimiters with
and without headers, mismatched header settings, and the intentionally
invalid headered fixture for the missing required `amount` column. Validation
mask tests verify which amount/date values are invalid. The suite also checks
that single-category and zero-revenue cases produce sensible insights, dates
in insights use full month names, and amounts with dollar signs and thousands
separators are counted for cleaning.

## Pipeline smoke check

Run the separate print-based sample pipeline check:

```powershell
.\venv\Scripts\python.exe tests\test_pipeline.py
```

It loads `data/sales/sales_sample_10.csv`, applies the cleaning functions,
calculates metrics and aggregations, and prints generated insights. This is a
small smoke check; the automated regression suite covers a broader set of
cases.

## Fixture inventory

| File | Scenario |
| --- | --- |
| `sales_sample_10.csv` | Small, ordinary sales dataset; used by the smoke script. |
| `sales_clean_100.csv` | Clean dataset with 100 rows. |
| `sales_clean_1000.csv` | Clean dataset with 1,000 rows. |
| `sales_messy_11.csv` | Small dataset with mixed data-quality issues. |
| `sales_messy_1000.csv` | Larger messy dataset with missing values, duplicate rows, inconsistent category capitalization/spelling, malformed dates, and formatted amounts. |
| `sales_custom_headers_8.csv` | Valid data under non-standard headers (`Transaction Date`, `Revenue`, `Department`, `Product`) plus an unused `Region` column; exercises column matching. Excluded from the exact-schema fixture test. |
| `sales_misspelled_categories_20.csv` | Twenty rows with typo categories (`Electonics`, `Clothng`, `Fodd`) and a legitimate rare category (`Toys`) that must not be flagged. |
| `sales_returns_100.csv` | Sales data including return/negative-amount cases. |
| `sales_single_category_50.csv` | Dataset with a single category. |
| `sales_validation_issues_5.csv` | Small dataset for validation and cleaning scenarios. |
| `sales_yearly_trend_365.csv` | Daily records spanning a year for date-oriented analysis. |
| `sales_zero_revenue_12.csv` | Zero-revenue edge case for safe KPI, chart, and insight behavior. |
| `sales_missing_amount_2.csv` | Intentionally invalid schema: required `amount` column is omitted. |
| `sales_no_headers_clean_8.csv` | Clean eight-row sales file with no header row. |
| `sales_no_headers_messy_6.csv` | Headerless six-row file with currency values, inconsistent category case, a missing amount, an invalid date, a negative amount, and a duplicate. |
| `sales_no_headers_semicolon_4.csv` | Headerless four-row sales file using semicolons. |
| `sales_no_headers_missing_column_2.csv` | Intentionally invalid headerless file with only three columns. |

### Inventory fixtures (`data/inventory/`)

| File | Scenario |
| --- | --- |
| `inventory_clean_100.csv` | One hundred clean rows with required and optional columns. |
| `inventory_messy_100.csv` | One hundred rows with duplicates, missing and negative numbers, category typos, a blank category, and formatted cost. |
| `inventory_negative_quantity.csv` | One negative quantity with otherwise valid rows. |
| `inventory_missing_cost.csv` | One missing unit cost with otherwise valid rows. |
| `inventory_missing_quantity.csv` | One missing quantity with otherwise valid rows. |
| `inventory_duplicates.csv` | Two repeated rows for duplicate detection and removal. |
| `inventory_low_stock.csv` | Items below, at, and above reorder levels. |
| `inventory_clean_20.csv` | Clean file with all six columns and one low-stock item. |
| `inventory_messy_20.csv` | 2 duplicate rows, a missing quantity and unit cost, a negative quantity and unit cost, misspelled categories (`Electonics`, `Clothng`, `Fodd`), a blank category, and `$`/comma unit costs. |
| `inventory_minimal_8.csv` | Only the four required columns (no low-stock check). |
| `inventory_custom_headers_6.csv` | Non-standard headers (`SKU`, `Department`, `Qty on Hand`, `Cost per Unit`, `Reorder Point`); exercises column matching. |
| `inventory_no_headers_5.csv` | Headerless, four columns. |
| `inventory_non_numeric_5.csv` | Text in quantity and unit cost; cleaning is blocked until the file is fixed. |
| `inventory_missing_column_5.csv` | No `unit_cost` column; blocked. |
| `inventory_zero_value_6.csv` | Every item has zero value; dashboard and insights must not crash or compare shares. |

### Expenses fixtures (`data/expenses/`)

| File | Scenario |
| --- | --- |
| `expenses_clean_100.csv` | One hundred clean rows for KPI, dashboard, and analysis coverage. |
| `expenses_messy_100.csv` | One hundred rows with duplicates, missing amounts, category typos, unreadable dates, and formatted amounts. |
| `expenses_custom_headers.csv` | Non-standard transaction, amount, category, and supplier headers for column mapping. |
| `expenses_duplicates.csv` | Repeated expense row for duplicate detection and removal. |
| `expenses_invalid_amount.csv` | Non-numeric amount that blocks cleaning. |
| `expenses_missing_amount.csv` | Missing amount for accept/reject fill behavior. |
| `expenses_missing_column.csv` | Missing required `vendor` column. |
| `expenses_no_headers.csv` | Headerless four-column expenses file. |
| `expenses_zero_total.csv` | Zero-amount rows for safe KPI and category-share handling. |

## Recorded development verification

On November 2, 2026, the full automated regression suite passed all 170 tests.
Coverage includes the Sales, Inventory, and Expenses workflow screens,
dataset-specific loaders and mappings, cleaning choices and reports,
dashboards, insights, date-only cleaned previews, and the bundled fixture
scenarios. The separate Sales pipeline smoke check also completed
successfully. These checks are automated development verification; they are
not a browser-based usability study or evidence of business impact.

Rerun the regression suite and smoke check after changes to loading, cleaning,
transformations, charting, or insight generation. Update this record with the
test date and results when verification is repeated.

## Suggested manual evaluation procedure

Upload-setting problems should be caught on the upload page with an
instruction to change a specific setting and choose the file again. Try: a
semicolon file with **Comma** selected (names **Semicolon**), a headerless file
with the header checkbox on (says the first row looks like data), a header-only
file (no data rows), an empty file, and a non-CSV file such as an image
renamed to `.csv`. None should show a Python error, and **Continue to data
checks** should not appear for the first three.

For each valid fixture:

1. Upload the file in the Streamlit app.
2. Confirm the required-column check passes and the preview/shape are shown.
3. Review validation counts and the recommended actions (each shows a
   **Preview** of the affected rows or values), then apply them.
   Repeat with each fix accepted and rejected: duplicates (**Remove
   duplicates**), missing amounts (**Apply fix**; rejecting leaves them empty
   and excluded from KPIs), and invalid dates (**Exclude from trends** or
   **Remove rows entirely**). For `sales_misspelled_categories_20.csv`, accept
   and reject each category correction (for example `Electonics → Electronics`)
   and confirm `Toys` is not flagged. Confirm the row counts shown under **Impact**.
4. Confirm the cleaning summary and cleaned preview appear.
5. Confirm the dashboard and insights load without an error.
6. On the dashboard, open **View cleaning report** and download it. Check that
   rows before/after match the cleaning summary, and that accepted fixes read
   "removed"/"replaced" while rejected fixes read "kept"/"left empty". For
   `sales_messy_1000.csv` with defaults: 1000 rows before, 990 after, 8 duplicates
   removed, 2 missing amounts replaced with 0, 5 invalid dates excluded from
   trends, 3 currency-formatted amounts converted, and 2 blank-category rows removed.
   If you matched columns, the report should list them.
7. For the zero-revenue fixture, confirm the UI explains unavailable revenue
   comparisons instead of failing.

For `sales_missing_amount_2.csv`, confirm that validation identifies
`amount` as missing, directs the user to correct and re-upload the CSV, offers
a **Back to Upload Data** action, and prevents cleaning and analysis. In the
**Match your columns** form, confirm that leaving `amount` as "(not in my
file)" is rejected with a message, and that no other column is suggested for it.

For `sales_custom_headers_8.csv`, confirm the form suggests `Transaction Date`,
`Revenue`, `Department`, and `Product`, that **Use these columns** removes the
missing-column error and ignores `Region`, and that cleaning then continues to
the dashboard. Also try choosing the same file column for two values and confirm
it is rejected.

For valid `sales_no_headers_*.csv` files, turn off the header-row checkbox,
select the fixture's delimiter, and confirm the app recognizes the columns in
the order `date`, `amount`, `category`, `item`. The clean, messy, and
semicolon-delimited files should proceed through cleaning and analysis. The
`sales_no_headers_missing_column_2.csv` fixture should report the three
columns read, show the required four-column order, explain that the missing
named field cannot be identified without headers, and not enable progression
to validation.

For files with headers, keep the header option on. In either header mode,
select the delimiter that matches the file. A mismatch should show a
parsing/schema message that names missing columns when they can be identified,
and should not allow cleaning with incorrectly named columns. For validation
examples, check that displayed row numbers refer to one-based CSV data rows
(not counting a header row), and that quoted values identify the problematic
cells.

For a final project evaluation, record the Python and package versions, test
date, observed outcomes, and any user-study results. Fixture tests check
technical behavior; they do not, by themselves, establish usability for a
broad user population.

## Suggested manual Inventory evaluation

For Inventory, select **Inventory** in the **Dataset type** dropdown and try:

1. Upload `inventory_clean_100.csv`. Confirm it reaches the checks page without
   recommendations, then continue to the dashboard and insights.
2. Upload `inventory_messy_100.csv`. Review duplicate, missing-value, negative
   number, and category recommendations. Accept and reject choices, and check
   that the cleaning report reflects the decisions.
3. Upload each issue-specific fixture. Confirm negative quantities are kept
   unless removal is chosen, missing quantities and costs can be filled
   independently, duplicate rows are reported, and low-stock detection
   includes quantities at or below reorder levels.
4. Upload `inventory_custom_headers_6.csv`. Confirm the suggested header
   matches are correct and that applying the mapping allows cleaning.
5. Upload `inventory_non_numeric_5.csv` and `inventory_missing_column_5.csv`.
   Confirm each blocks cleaning and offers **Back to Upload Data**.
6. Upload `inventory_minimal_8.csv` and `inventory_zero_value_6.csv`. Confirm
   the missing optional reorder-level column disables low-stock checks and
   zero-value data renders without invalid comparisons.

The headless AppTest suite exercises the upload page, custom-header mapping,
recommended actions, cleaning, dashboard, insights, blocked-input cases, and
the dataset-type reset. This manual procedure is an additional visual check,
not a substitute for automated tests.

## Suggested manual Expenses evaluation

Select **Expenses** from the **Dataset type** dropdown and try:

1. Upload `expenses_clean_100.csv`, continue through checks, dashboard, and
   insights, and verify the four requested KPI cards.
2. Upload `expenses_messy_100.csv`. Review duplicate, missing amount, invalid
   date, and category-correction recommendations; accept and reject choices,
   then verify the cleaning report.
3. Upload `expenses_custom_headers.csv` and confirm that the transaction date,
   expense amount, department, and supplier headers are suggested and can be
   applied.
4. Upload `expenses_invalid_amount.csv` and `expenses_missing_column.csv`.
   Confirm non-numeric amounts and missing required fields block cleaning and
   provide a route back to upload.
5. Upload `expenses_zero_total.csv` and confirm no invalid share comparison is
   shown. Use `expenses_no_headers.csv` with the header option off and check
   that the required four-column order is assigned.
6. On the dashboard, check that cleaned preview dates display as calendar
   dates without `00:00:00`; downloaded CSV values remain suitable for data
   processing.

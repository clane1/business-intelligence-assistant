# Business Intelligence Assistant

A guided Streamlit app for checking Sales, Inventory, or Expenses spreadsheets,
fixing common data issues, and exploring business metrics, charts, and
plain-language highlights.

> **Current scope:** Three dataset types are supported, chosen from the
> **Dataset type** dropdown on the upload page. **Sales** needs `date`,
> `amount`, `category`, and `item`; **Inventory** needs `item`, `category`,
> `quantity`, and `unit_cost` with optional `reorder_level` and
> `last_updated`; **Expenses** needs `date`, `amount`, `category`, and
> `vendor`. Columns with other names can be matched on the check page.
> Headerless CSVs must contain their required columns in the documented
> order. Switching dataset type clears the current upload. This prototype
> processes data in memory and does not persist uploads to a database.

## Quick start (Windows)

From the repository root, create and activate a virtual environment, install
the app's Python packages, and start Streamlit:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install pandas streamlit altair
python -m streamlit run frontend\streamlit_app_v2.py
```

If PowerShell blocks environment activation, run the commands using the
environment's interpreter directly:

```powershell
.\venv\Scripts\python.exe -m pip install pandas streamlit altair
.\venv\Scripts\python.exe -m streamlit run frontend\streamlit_app_v2.py
```

Open the local URL printed by Streamlit in a browser. To stop the server, press
`Ctrl+C` in the terminal where it is running.

## Use the application

1. Choose **Sales**, **Inventory**, or **Expenses** from **Dataset type**, then
   upload a CSV for that dataset. Requirements and an example appear below
   the uploader.
2. Check which columns are present, review data-quality metrics, and preview
   the upload. The check page shows **Data summary**, **Data quality metrics**,
   **Recommended actions**, and **Apply fixes**.
3. Review the recommendations for the selected dataset. Sales checks
   duplicates, missing amounts, unreadable dates, and likely category typos.
   Inventory checks duplicates, missing quantities or unit costs, negative
   quantities or costs, and likely category typos. Expenses checks duplicates,
   missing amounts, unreadable dates, and likely category typos. Review each
   preview, accept or reject the suggested action, then apply the choices; the
   uploaded data is not modified.
4. Explore the dataset-specific dashboard and generated insights. All three
   workflows provide a cleaning report and downloads for the cleaned CSV and
   insights.

### Sales data

Sales requires `date`, `amount`, `category`, and `item`. If a headered file
uses different names (for example `Transaction Date`, `Revenue`, `Department`,
`Product`), the check page shows a **Match your columns** form with suggestions
filled in. Confirm it and the app uses your columns under the required names;
other columns in the file are not used. If a required value isn't in your file
at all, validation names it, blocks cleaning, and provides a **Back to Upload
Data** action so you can correct the CSV and upload it again. A missing column
is different from an empty cell: empty cells are listed by column and filled
with the app's documented defaults during cleaning.

When the first row does not contain column names, uncheck **The first row
contains column names**. Headerless files must contain exactly four columns in
this order: `date`, `amount`, `category`, `item`. The selected delimiter still
applies. If a headerless file has a different number of columns, the upload
error reports the number read and the required order. Since there are no
column names, the app cannot identify which field is missing.

Headerless sales files must contain the four required columns in that order.
CSV parsing uses a generic file reader and a sales-specific wrapper that
checks this schema and provides upload-specific format errors.

The app can clean amounts that contain dollar signs or commas, fill supported
empty cells, remove repeated rows, and make category names consistent.
Non-numeric, non-empty amount values cannot be cleaned automatically; the
validation screen reports example values and CSV data-row numbers so they can
be corrected before cleaning. Unreadable dates are reported with example
values and data-row numbers, then excluded from date-based charts and insights;
their amounts still count in sales totals. Use year-month-day dates such as
`2024-01-31` when possible. The trend chart groups sales by day, week, or
month depending on the date span.

If a file includes negative amounts, they reduce the sales total and may
represent refunds or returns.

### Inventory data

Inventory requires `item`, `category`, `quantity`, and `unit_cost`. The
optional `reorder_level` column enables low-stock checks; `last_updated` can be
included as a descriptive field. Non-standard headers can be matched on the
check page. Headerless inventory files must provide the four required columns
in that order; optional columns require headers.

Non-numeric, non-empty quantities and unit costs block cleaning until the
source file is corrected. Missing quantities and unit costs can each be
replaced with zero. Dollar signs and commas in unit costs are supported.
Negative quantities and costs are kept by default because they may be
meaningful or may indicate errors; the user can choose to remove affected
rows. Inventory value is calculated as `quantity × unit_cost`. The dashboard
shows total value, units, unique items, value by category, and highest-value
items. If `reorder_level` is present, it also identifies items at or below
their reorder level.

### Expenses data

Expenses requires `date`, `amount`, `category`, and `vendor`. Headered files
may use other column names; map them on the check page. Headerless files must
provide those four columns in that order. Non-numeric, non-empty amounts block
cleaning, while missing amounts can be replaced with zero or left empty.
Duplicates and likely category typos are reviewable actions. Invalid dates can
be kept in total expenses while excluded from the trend, or removed with their
rows.

The dashboard reports total and average expenses, expense records, the largest
expense category, expenses by category, an expense trend, category spending
shares, and spending by vendor. Insights highlight category share, the highest
trend period, and the largest vendor. Cleaned-data previews show dates as
readable calendar dates without a midnight time; the downloaded data retains
its date values for analysis.

## Tests

Run the automated tests from the repository root:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_[a-oq-z]*.py"
```

They cover validation and cleaning, recommendations and category suggestions,
column mapping, upload diagnosis, the cleaning report, dashboard calculations,
all Sales, Inventory, and Expenses CSV fixtures, and headless runs of the whole
app workflow for each dataset type. A
separate sample-data smoke check is also available:

```powershell
.\venv\Scripts\python.exe tests\test_pipeline.py
```

## Project documentation

- [Architecture and workflow](docs/architecture.md)
- [Testing Sales, Inventory, and Expenses](docs/testing.md)
- [Capstone report draft](docs/capstone_report_draft.md)
- [Formatted report PDF](docs/Business_Intelligence_Assistant_Report.pdf)

Sample and test CSV files are in [data/sales](data/sales/),
[data/inventory](data/inventory/), and [data/expenses](data/expenses/).

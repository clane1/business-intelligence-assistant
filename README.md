# Business Intelligence Assistant

A guided Streamlit app for checking a sales spreadsheet, fixing common data
issues, and viewing sales totals, charts, and plain-language highlights.

> **Current scope:** Sales Data is the only supported dataset type. CSV files
> need `date`, `amount`, `category`, and `item` columns. For files without a
> header row, select the no-header option and provide those four columns in
> that exact order. This prototype processes data in memory and does not
> persist uploads to a database.

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

1. Upload a sales CSV.
2. Check which columns are present, review empty cells and unusual dates, and
   preview the uploaded file.
3. Run cleaning when the required columns are present; review the cleaning
   summary and cleaned-data preview.
4. Explore the dashboard and generated insights.

When the first row does not contain column names, uncheck **The first row
contains column names**. Headerless files must contain exactly four columns in
this order: `date`, `amount`, `category`, `item`. The selected delimiter still
applies. The app reports a clear error if a headerless file has a different
number of columns.

CSV parsing is handled by a generic file reader and a sales-specific wrapper:
the generic reader parses the chosen delimiter/header mode, while the sales
wrapper checks the required sales column order and provides upload-specific
format errors.

The app can clean amounts that contain dollar signs or commas, fill supported
empty cells, remove repeated rows, and make category names consistent. Use
year-month-day dates such as `2024-01-31` when possible. Dates the app cannot
read are left out of the sales trend and date-related insights, but their
amounts still count in sales totals.
The trend chart groups sales by day, week, or month depending on the date span.

If a file includes negative amounts, they reduce the sales total and may
represent refunds or returns.

## Tests

Run the automated regression tests from the repository root:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_sales_trend.py" -v
```

The tests check date parsing, daily/weekly/monthly trend selection and labels,
and all sales CSV fixtures. The fixture with the missing `amount` column must
be rejected. A separate sample-data smoke check is also available:

```powershell
.\venv\Scripts\python.exe tests\test_pipeline.py
```

## Project documentation

- [Architecture and workflow](docs/architecture.md)
- [Testing and sales fixtures](docs/testing.md)
- [Capstone report draft](docs/capstone_report_draft.md)
- [Formatted report PDF](docs/Business_Intelligence_Assistant_Report.pdf)

Sample and test CSV files are in [data/sales](data/sales/).

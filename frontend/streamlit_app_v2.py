"""
streamlit_app_v2.py

Business Intelligence Assistant

CMPT 496 Capstone Project

Version 2

This version follows the guided workflow
shown in the Figma prototype.

Workflow:

1. Upload Data
2. Validation
3. Dashboard
4. Insights

Users cannot skip ahead until previous
steps have been completed.

CSV parsing is delegated to ``backend.load_csv`` through
``backend.csv_loader``; this page handles the user-facing upload, workflow,
validation, cleaning, dashboard, and insight presentation.
"""

# ==========================================
# IMPORTS
# ==========================================

import os
import sys
import pandas as pd
import streamlit as st

# ==========================================
# PROJECT PATH SETUP
# ==========================================

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

# ==========================================
# BACKEND MODULES
# ==========================================

from backend.transformation import (
    calculate_kpis,
    sales_by_category,
    sales_by_time_period,
    category_distribution
)

from backend.csv_loader import (
    SalesCsvFormatError,
    load_sales_csv,
)

from backend.insights import (
    generate_insights
)

from backend.validation import (
    validate_columns,
    validate_missing,
    validate_types,
    count_invalid_dates,
    count_duplicates,
    count_currency_values,
    invalid_amount_mask,
    invalid_date_mask,
)

from backend.cleaning import (
    clean_missing,
    clean_types,
    clean_dates,
    clean_duplicates,
    normalize_categories
)

from backend.recommendations import (
    CleaningChoices,
    build_recommendations,
    clean_with_choices,
    suggest_category_corrections,
)

from backend.column_mapping import (
    ColumnMappingError,
    apply_mapping,
    suggest_mapping,
)

from backend.cleaning_report import build_cleaning_report

from backend.upload_diagnosis import diagnose_upload

from frontend.charts import format_display_date, render_sales_trend

REVIEW_WIDGET_KEYS = (
    "fix_duplicates",
    "fix_missing_amounts",
    "invalid_date_handling",
)
NOT_IN_FILE = "(not in my file)"
EXCLUDE_FROM_TRENDS = "Exclude from trends (keep the sales values)"
REMOVE_DATE_ROWS = "Remove rows entirely"
APPLY_CORRECTION = "Apply correction"
KEEP_ORIGINAL = "Keep original value"


def _format_count(count: int | str, item: str) -> str:
    """Format a count with singular/plural wording or pass text through.

    Text values are used for unavailable measurements; numeric values receive
    the given item label with a plural suffix when needed.
    """
    if isinstance(count, str):
        return count
    suffix = "" if count == 1 else "s"
    return f"{count} {item}{suffix}"


def _format_problem_examples(
    df: pd.DataFrame,
    mask: pd.Series,
    column: str,
) -> str:
    """Format up to five invalid values with their CSV data-row numbers."""
    positions = [position for position, invalid in enumerate(mask) if invalid]
    examples = []
    for position in positions[:5]:
        value = df.iloc[position][column]
        display_value = "(blank)" if pd.isna(value) else repr(value)
        examples.append(f"row {position + 1}: {display_value}")

    message = "; ".join(examples)
    if len(positions) > 5:
        message += f"; and {len(positions) - 5} more"
    return message


# ==========================================
# PAGE SETTINGS
# ==========================================

st.set_page_config(
    page_title="Clarity",
    page_icon="📊",
    layout="wide"
)

st.markdown(
    """
<style>

/* Sidebar */

section[data-testid="stSidebar"] {
    background-color: #0b2f1d;
}

/* Sidebar text */

section[data-testid="stSidebar"] * {
    color: white;
}

/* Sidebar buttons */

section[data-testid="stSidebar"] .stButton button {
    color: white !important;
    background-color: #174229;
    border: 1px solid #ffffff33;
    border-radius: 10px;
}

section[data-testid="stSidebar"] .stButton button p {
    color: white !important;
    font-weight: 600;
}

/* Hover effect */

section[data-testid="stSidebar"] .stButton button:hover {
    background-color: #1c5433;
}

/* Links and tables */

a {
    text-decoration: none;
    color: #464feb;
}

div[data-testid="stMarkdownContainer"] table th,
div[data-testid="stMarkdownContainer"] table td {
    border: 1px solid #e6e6e6;
}

div[data-testid="stMarkdownContainer"] table th {
    background-color: #f5f5f5;
    color: #263238 !important;
    font-weight: 600;
}

/* KPI cards */

[data-testid="metric-container"] {
    border: 1px solid #d9ded8;
    border-radius: 12px;
    padding: 15px;
}

</style>
""",
    unsafe_allow_html=True
)

# ==========================================
# SESSION STATE VARIABLES
# ==========================================
#
# Streamlit reruns the entire script whenever
# a user interacts with the application.
#
# Session State allows information to remain
# available between workflow steps.
#
# These variables control:
#
# current_step
#     Tracks which workflow screen is active
#
# raw_df
#     Stores the uploaded dataset before
#     cleaning and transformation
#
# clean_df
#     Stores the cleaned dataset after the
#     validation and cleaning stages
#
# dataset_type
#     Stores the selected analysis type
#     chosen by the user
#
# ==========================================

if "current_step" not in st.session_state:
    st.session_state.current_step = 1

if "raw_df" not in st.session_state:
    st.session_state.raw_df = None

if "clean_df" not in st.session_state:
    st.session_state.clean_df = None

if "cleaning_summary" not in st.session_state:
    st.session_state.cleaning_summary = None

if "source_df" not in st.session_state:
    st.session_state.source_df = None

if "column_mapping" not in st.session_state:
    st.session_state.column_mapping = None

if "source_name" not in st.session_state:
    st.session_state.source_name = None

if "cleaning_report" not in st.session_state:
    st.session_state.cleaning_report = None

# ==========================================
# WORKFLOW SIDEBAR
# ==========================================
#
# The sidebar functions as a workflow guide.
#
# Users complete the application in stages:
#
# Step 1 -> Upload Data
# Step 2 -> Validation
# Step 3 -> Dashboard
# Step 4 -> Insights
#
# Later stages remain locked until previous
# stages have been completed.
#
# This prevents users from skipping critical
# processing steps and mirrors the workflow
# proposed in the Figma prototype.
#
# ==========================================

with st.sidebar:

    st.title("Clarity")

    st.markdown(
        "### Analysis Workflow"
    )

    # ----------------------
    # STEP 1
    # ----------------------

    if st.button(
        "01 Upload Data",
        use_container_width=True
    ):
        st.session_state.current_step = 1

    # ----------------------
    # STEP 2
    # ----------------------

    if st.session_state.current_step >= 2:

        if st.button(
            "02 Check your data",
            use_container_width=True
        ):
            st.session_state.current_step = 2

    else:
        st.caption("🔒 Check your data")

    # ----------------------
    # STEP 3
    # ----------------------

    if st.session_state.current_step >= 3:

        if st.button(
            "03 Dashboard",
            use_container_width=True
        ):
            st.session_state.current_step = 3

    else:
        st.caption("🔒 Dashboard")

    # ----------------------
    # STEP 4
    # ----------------------

    if st.session_state.current_step >= 4:

        if st.button(
            "04 Insights",
            use_container_width=True
        ):
            st.session_state.current_step = 4

    else:
        st.caption("🔒 Insights")

    st.divider()

    # ----------------------
    # RESET
    # ----------------------

    if st.button(
        "🔄 Start New Analysis",
        use_container_width=True
    ):

        st.session_state.current_step = 1
        st.session_state.raw_df = None
        st.session_state.clean_df = None
        st.session_state.cleaning_summary = None
        st.session_state.source_df = None
        st.session_state.source_name = None
        st.session_state.cleaning_report = None
        st.session_state.column_mapping = None
        for key in list(st.session_state.keys()):
            if (
                key in REVIEW_WIDGET_KEYS
                or key.startswith(("fix_category_", "map_"))
            ):
                del st.session_state[key]
        st.rerun()

# ==========================================
# STEP 1 - DATA UPLOAD
# ==========================================
#
# Purpose:
#     Collect user data and dataset settings.
#
# Functions:
#     - Select dataset type
#     - Configure CSV options
#     - Upload CSV file
#     - Store uploaded data in Session State
#
# Output:
#     raw_df
#
# Once a file is parsed successfully, users
# may continue to validation. Required-column
# and data-quality issues are reported there.
#
# ==========================================


if st.session_state.current_step == 1:

    st.subheader(
        "Step 1 of 4"
    )

    st.title("Upload your sales data")

    st.write(
        "Choose a sales CSV file. The app will check it and show any issues "
        "before cleaning the data."
    )

    # --------------------------------------
    # DATASET TYPE SELECTION
    # --------------------------------------
    #
    # Allows users to specify what kind of
    # business dataset is being analysed.
    #
    # Currently:
    #     Sales Data is supported
    #
    # Future versions may support:
    #     Inventory Data
    #     Expense Data
    #     Customer Data
    #
    # --------------------------------------

    st.markdown("**Dataset type:** Sales data")

    # --------------------------------------
    # CSV IMPORT SETTINGS
    # --------------------------------------
    #
    # Allows users to specify how their file
    # is structured.
    #
    # First row contains headers:
    #     Determines whether column names
    #     exist in the first row.
    #
    # Delimiter:
    #     Defines how columns are separated.
    #
    # Common examples:
    #
    # Comma:
    #     date,amount,category
    #
    # Semicolon:
    #     date;amount;category
    #
    # Tab:
    #     date amount category
    #
    # --------------------------------------


    headers_included = st.checkbox(
        "The first row contains column names",
        value=True
    )

    if not headers_included:
        st.info(
            "Without a header row, columns must be in this order: "
            "date, amount, category, item."
        )

    delimiter = st.selectbox(
        "What separates the columns?",
        [
            "Comma",
            "Tab",
            "Semicolon"
        ]
    )

    # --------------------------------------
    # FILE UPLOAD
    # --------------------------------------
    #
    # Uploads the dataset and converts it into
    # a Pandas DataFrame.
    #
    # The DataFrame is saved in Session State
    # so it can be reused by later workflow
    # stages without requiring additional
    # uploads.
    #
    # --------------------------------------


    uploaded_file = st.file_uploader(
        "Choose your sales CSV file",
        type=["csv"]
    )

    # Upload results appear directly under the
    # uploader, above the requirements below.
    upload_status = st.container()

    if uploaded_file is not None:
        # Convert user-friendly delimiter names
        # into values understood by Pandas.
        #
        # Example:
        #
        # "Comma" -> ","
        # "Tab" -> "\t"
        #


        delimiter_map = {
            "Comma": ",",
            "Tab": "\t",
            "Semicolon": ";"
        }

        try:
            df = load_sales_csv(
                uploaded_file,
                delimiter=delimiter_map[delimiter],
                headers_included=headers_included,
            )
        except SalesCsvFormatError as error:
            upload_status.error(str(error))
        else:
            problem = diagnose_upload(
                df,
                delimiter_map[delimiter],
                headers_included,
            )
            if problem:
                upload_status.warning(problem)
            else:
                # Store uploaded dataset so that it can
                # be accessed by validation, cleaning,
                # dashboard, and insight-generation
                # modules later in the workflow.

                st.session_state.raw_df = df
                st.session_state.source_df = df
                st.session_state.source_name = uploaded_file.name
                st.session_state.column_mapping = None
                for key in list(st.session_state.keys()):
                    if key.startswith("map_"):
                        del st.session_state[key]
                st.session_state.cleaning_summary = None

                upload_status.success(
                    "Dataset uploaded successfully."
                )

                # Once the dataset has been uploaded
                # successfully, the user may proceed
                # to the validation stage.
                #
                # Updating current_step causes the
                # application to render Step 2.

                if upload_status.button(
                    "Continue to data checks"
                ):
                    st.session_state.current_step = 2
                    st.rerun()

    # --------------------------------------
    # REQUIRED CSV FORMAT AND EXAMPLE
    # --------------------------------------
    #
    # Guidance follows the upload control so
    # the primary action comes first.
    #
    # --------------------------------------

    st.markdown("### Sales data requirements")

    st.info(
        "Sales data is the only supported type right now. Amounts may include "
        "dollar signs and commas. For best results, enter dates in "
        "year-month-day order, like 2024-01-31. Dates the app cannot read "
        "aren't shown in the sales trend or date-related insights, but their "
        "sales amounts still count "
        "in the totals."
    )

    st.markdown(
        """
    ### Columns your file needs

    | Column name | What it means | Example |
    |----------|----------|----------|
    | `date` | Date of the sale | 2024-01-01 |
    | `amount` | Sale amount | 25.48 |
    | `category` | Product category | Electronics |
    | `item` | Product or service sold | Mouse |
    """
    )

    st.markdown("### Example dataset")

    st.code(
        "date,amount,category,item\n"
        "2024-01-01,25.48,Electronics,Mouse\n"
        "2024-01-02,15.99,Food,Coffee\n"
        "2024-01-03,63.99,Clothing,Jacket\n"
        "2024-01-04,119.99,Electronics,Monitor\n"
    )


# ==========================================
# STEP 2 - VALIDATION
# ==========================================
#
# Purpose:
#     Evaluate dataset quality before
#     cleaning and analysis.
#
# Validation checks include:
#
#     - Required columns
#     - Missing values
#     - Data type issues
#     - Example values and row numbers for
#       invalid amounts and dates
#
# Results are presented to the user before
# any cleaning operations are performed.
# Missing required columns and non-numeric
# amounts block cleaning.
#
# ==========================================
if st.session_state.current_step == 2:

    st.subheader(
        "Step 2 of 4"
    )

    st.title("Check your data")

    df = st.session_state.raw_df
    
    # Required fields for the Sales Data
    # workflow.
    #
    # Future dataset types may require
    # different column definitions.

    required_columns = [
        "date",
        "amount",
        "category",
        "item"
    ]

    # Verify that all mandatory fields
    # exist within the uploaded dataset.
    missing_columns = validate_columns(
        df,
        required_columns
    )

    st.header("Data summary")

    st.subheader("Dataset Preview")
    st.dataframe(
        df.head(10),
        use_container_width=True
    )

    st.subheader("Your file at a glance")
    st.write(
        f"{len(df)} rows and {len(df.columns)} columns"
    )

    if missing_columns:
        if len(missing_columns) == 1:
            st.error(
                f"Your file is missing the required {missing_columns[0]} column."
            )
        else:
            st.error(
                "Your file is missing these required columns: "
                f"{', '.join(missing_columns)}."
            )
        if len(df.columns) == 1:
            st.warning(
                "Only one column was read, so the file's separator probably "
                "doesn't match the **What separates the columns?** setting."
            )
        st.markdown(
            "**How to fix this**\n\n"
            "1. If your file uses different names for these values (for "
            "example *Revenue* instead of *amount*), match them in the "
            "**Match your columns** form below.\n"
            "2. If the preview above looks wrong (everything in one column, "
            "or the first row is data), click **Back to Upload Data**, "
            "change the **separator** or **first row contains column "
            "names** setting, and choose your file again.\n"
            "3. If a required column really isn't in your file, add it in "
            "your spreadsheet, save as CSV, click **Back to Upload Data**, "
            "and choose the corrected file."
        )
        if st.button("Back to Upload Data"):
            st.session_state.current_step = 1
            st.rerun()
    else:
        st.success(
            "Your file has all the columns needed for sales analysis."
        )

    # --------------------------------------
    # COLUMN MATCHING
    # --------------------------------------
    #
    # Lets users map their own column names
    # (e.g. Revenue) to the required ones.
    # Suggestions come from known aliases and
    # close spellings; nothing is applied
    # until the user confirms.
    #
    # --------------------------------------

    source_df = st.session_state.source_df
    if source_df is not None and validate_columns(source_df, required_columns):
        applied_mapping = st.session_state.column_mapping
        if applied_mapping:
            st.caption(
                "Columns matched: "
                + ", ".join(
                    f"{source} → {target}"
                    for target, source in applied_mapping.items()
                )
                + ". Other columns in your file are not used."
            )

        with st.expander(
            "Match your columns" if missing_columns else "Change column matching",
            expanded=bool(missing_columns),
        ):
            st.write(
                "Choose which column in your file provides each value the "
                "app needs. Suggestions are filled in where a name looks "
                "similar."
            )
            suggestions = applied_mapping or suggest_mapping(
                list(source_df.columns)
            )
            options = [NOT_IN_FILE] + [str(c) for c in source_df.columns]
            chosen = {}
            for target in required_columns:
                suggested = suggestions.get(target)
                default = (
                    options.index(str(suggested))
                    if suggested is not None and str(suggested) in options
                    else 0
                )
                choice = st.selectbox(
                    f"{target.capitalize()} column",
                    options,
                    index=default,
                    key=f"map_{target}",
                )
                chosen[target] = None if choice == NOT_IN_FILE else choice

            if st.button("Use these columns"):
                try:
                    st.session_state.raw_df = apply_mapping(
                        source_df.rename(columns=str), chosen
                    )
                except ColumnMappingError as error:
                    st.error(str(error))
                else:
                    st.session_state.column_mapping = chosen
                    for key in list(st.session_state.keys()):
                        if (
                            key in REVIEW_WIDGET_KEYS
                            or key.startswith("fix_category_")
                        ):
                            del st.session_state[key]
                    st.rerun()

    # --------------------------------------
    # VALIDATION SUMMARY
    # --------------------------------------
    #
    # Provides a high-level overview of
    # dataset quality before cleaning.
    #
    # This helps users quickly understand
    # the condition of the uploaded file.
    #
    # --------------------------------------

    total_missing = validate_missing(df).sum()

    st.divider()
    st.header("Data quality metrics")

    invalid_dates = (
        count_invalid_dates(df)
        if "date" in df.columns
        else "Unavailable"
    )
    duplicate_rows = count_duplicates(df)
    currency_values = (
        count_currency_values(df)
        if "amount" in df.columns
        else "Unavailable"
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Rows in file",
        len(df)
    )

    col2.metric(
        "Empty cells",
        total_missing
    )

    col3.metric(
        "Dates the app can't read",
        invalid_dates
    )

    col4.metric(
        "Repeated rows",
        duplicate_rows
    )

    col5.metric(
        "Amounts with $ or commas",
        currency_values
    )

    if "date" in df.columns and invalid_dates > 0:
        invalid_date_examples = _format_problem_examples(
            df,
            invalid_date_mask(df),
            "date",
        )
        st.warning(
            f"The app couldn't read {invalid_dates} date(s). Their sales "
            "amounts will still count in the totals, but these rows won't "
            "appear in the sales trend or date-related insights. "
            f"Problem values: {invalid_date_examples}."
        )

    if missing_columns:
        st.info(
            "Some checks aren't available until you add all required columns."
        )
    else:
        st.info(
            f"Your file has {_format_count(total_missing, 'empty cell')}, "
            f"{_format_count(duplicate_rows, 'repeated row')}, "
            f"{_format_count(currency_values, 'amount with dollar signs or commas')}, "
            f"and {_format_count(invalid_dates, 'unreadable date')}. Review the "
            "recommended actions below; nothing changes until you apply them."
        )

    st.subheader(
        "Empty cells by column"
    )

    st.dataframe(
        # Identify missing or empty values that
        # may affect downstream processing.
        validate_missing(df).rename("Empty cells").to_frame()
    )

    st.subheader(
        "Check the amount format"
    )
    
    # Inspect columns for possible data
    # type inconsistencies.
    #
    # Example:
    #     Text appearing in numeric fields.


    issues = validate_types(df)

    if missing_columns:
        st.info("Amount checks are unavailable until the required columns are present.")
    elif issues.get("amount") == "Non-numeric values detected":
        invalid_amounts = invalid_amount_mask(df)
        invalid_amount_examples = _format_problem_examples(
            df,
            invalid_amounts,
            "amount",
        )
        st.error(
            f"{int(invalid_amounts.sum())} value(s) in the amount column "
            "aren't numbers and can't be cleaned automatically. These rows "
            f"need correcting: {invalid_amount_examples}."
        )
        st.markdown(
            "**How to fix this:** open your file in a spreadsheet, replace "
            "or delete those values in the amount column (row numbers count "
            "data rows, not the header), save as CSV, then click **Back to "
            "Upload Data** and choose the corrected file."
        )
        if st.button("Back to Upload Data", key="back_amounts"):
            st.session_state.current_step = 1
            st.rerun()
    elif issues.get("amount") == "Currency-formatted values require cleaning":
        st.info(
            "Some amounts include dollar signs or commas. The app will "
            "remove those when it cleans the data."
        )

    else:
        st.success("Sale amounts look ready to use.")


    # Execute the cleaning pipeline.
    #
    # The cleaning module performs:
    #
    #     Missing value handling
    #     Data type correction
    #     Date normalisation
    #     Duplicate removal
    #     Category standardisation
    #
    # The cleaned data is stored in Session
    # State and the user advances to the
    # Dashboard stage.
    # Review the suggested fixes. Nothing is
    # changed until the user confirms below.
    choices = CleaningChoices()
    no_fixes_needed = False
    cleaning_blocked = bool(
        missing_columns
        or issues.get("amount") == "Non-numeric values detected"
    )

    if not missing_columns:
        st.divider()
        st.header("Recommended actions")
        recommendations = build_recommendations(df)
        category_corrections = suggest_category_corrections(df)

        if not recommendations and not category_corrections:
            no_fixes_needed = True
            st.success("No fixes are needed for duplicates, missing amounts, dates, or category spelling.")

        choice_values = {
            "remove_duplicates": False,
            "fill_missing_amounts": False,
            "remove_invalid_date_rows": False,
        }
        accepted_corrections = {}

        if category_corrections:
            with st.container(border=True):
                st.subheader(
                    f"{_format_count(len(category_corrections), 'possible category misspelling')} found"
                )
                st.markdown(
                    "**Suggested fix:** Rename uncommon spellings to the "
                    "similar category used more often"
                )
                st.markdown(
                    "**Impact:** Sales are grouped under the corrected "
                    "category in charts and insights."
                )
                for correction in category_corrections:
                    st.markdown(
                        f"**{correction.original} → {correction.suggestion}** "
                        f"({_format_count(correction.count, 'row')})"
                    )
                    st.markdown(f"**Preview:** {correction.preview}")
                    decision = st.radio(
                        f"Choice for {correction.original}",
                        [APPLY_CORRECTION, KEEP_ORIGINAL],
                        key=f"fix_category_{correction.original}",
                        horizontal=True,
                        label_visibility="collapsed",
                    )
                    if decision == APPLY_CORRECTION:
                        accepted_corrections[correction.original] = (
                            correction.suggestion
                        )
        for recommendation in recommendations:
            with st.container(border=True):
                st.subheader(recommendation.title)
                st.markdown(f"**Suggested fix:** {recommendation.suggested_fix}")
                st.markdown(f"**Impact:** {recommendation.impact}")
                if recommendation.examples:
                    st.markdown(
                        "**Examples:**\n\n"
                        + "\n".join(f"- {example}" for example in recommendation.examples)
                    )
                else:
                    st.markdown(f"**Preview:** {recommendation.preview}")

                if recommendation.key == "duplicates":
                    choice_values["remove_duplicates"] = st.checkbox(
                        "Remove duplicates",
                        value=True,
                        key="fix_duplicates",
                    )
                elif recommendation.key == "missing_amounts":
                    choice_values["fill_missing_amounts"] = st.checkbox(
                        "Apply fix",
                        value=True,
                        key="fix_missing_amounts",
                    )
                elif recommendation.key == "invalid_dates":
                    date_choice = st.radio(
                        "How should these rows be handled?",
                        [EXCLUDE_FROM_TRENDS, REMOVE_DATE_ROWS],
                        key="invalid_date_handling",
                    )
                    choice_values["remove_invalid_date_rows"] = (
                        date_choice == REMOVE_DATE_ROWS
                    )

        choices = CleaningChoices(
            **choice_values,
            category_corrections=accepted_corrections,
        )

    # Execute the cleaning pipeline with the
    # accepted fixes. The cleaned data is stored
    # in Session State and the user advances to
    # the Dashboard stage.
    st.divider()
    if cleaning_blocked:
        st.header("Apply fixes")
        st.warning(
            "Cleaning is unavailable until the problem above is fixed: "
            + (
                "a required column is missing."
                if missing_columns
                else "some amounts aren't numbers."
            )
            + " Fix it in your file and upload it again."
        )
        apply_label = "Apply selected fixes and view dashboard"
    elif no_fixes_needed:
        st.header("Continue")
        st.write(
            "There's nothing to review. Routine formatting, such as "
            "removing dollar signs and standardizing category capitalization, "
            "is still applied to a copy of your data. Your uploaded file is "
            "not changed."
        )
        apply_label = "Continue to dashboard"
    else:
        st.header("Apply fixes")
        st.write(
            "Your choices above are applied to a copy of your data. Your "
            "uploaded file is not changed."
        )
        apply_label = "Apply selected fixes and view dashboard"
    if st.button(
        apply_label,
        disabled=cleaning_blocked
    ):
        df, cleaning_summary = clean_with_choices(df, choices)

        if df.empty:
            st.error(
                "No rows remain after cleaning, because every row has a "
                "blank category. Add category values in your file, then go "
                "back to Upload Data and choose the corrected file."
            )
        else:
            st.session_state.clean_df = df
            st.session_state.cleaning_summary = cleaning_summary
            st.session_state.cleaning_report = build_cleaning_report(
                cleaning_summary,
                source_name=st.session_state.source_name,
                column_mapping=st.session_state.column_mapping,
            )
            st.session_state.current_step = 3
            st.rerun()

# ==========================================
# STEP 3 - DASHBOARD
# ==========================================
#
# Purpose:
#     Generate visual analytics from the
#     cleaned dataset.
#
# Dashboard features:
#
#     - KPI summaries
#     - Category analysis
#     - Sales trend analysis
#     - Revenue distribution
#
# Data source:
#     clean_df
#
# Output:
#     KPI cards
#     Charts
#     Downloadable cleaned dataset
#
# ==========================================

if st.session_state.current_step == 3:

    st.subheader(
        "Step 3 of 4"
    )

    st.title(
        "Sales dashboard"
    )
    
    # Retrieve the cleaned dataset produced
    # during Step 2. The dashboard should
    # always operate on cleaned data rather
    # than the originally uploaded dataset.

    df = st.session_state.clean_df

    # --------------------------------------
    # KPI GENERATION
    # --------------------------------------
    #
    # KPI (Key Performance Indicator)
    # calculations provide a high-level
    # summary of business performance.
    #
    # Current KPIs:
    #
    #     - Total Sales
    #     - Average Sale Value
    #     - Transaction Count
    #     - Top Category
    #
    # Future versions may include:
    #
    #     - Highest Sale
    #     - Lowest Sale
    #     - Revenue Growth
    #
    # --------------------------------------

    kpis = calculate_kpis(df)
    category_df = sales_by_category(df)

    if st.session_state.cleaning_summary:
        summary = st.session_state.cleaning_summary
        st.subheader("What the app changed")
        st.success(
            f"Kept {summary['rows_after']} of {summary['rows_before']} rows. "
            f"Removed {_format_count(summary['duplicates_removed'], 'repeated row')} "
            f"and {_format_count(summary['category_rows_removed'], 'category row')} "
            "with blank or unrecognized names. "
            f"Filled {_format_count(summary['missing_cells_filled'], 'empty cell')}. "
            + (
                f"Corrected the spelling of {_format_count(summary['categories_corrected'], 'category row')}. "
                if summary["categories_corrected"] else ""
            )
            + (
                f"Left {_format_count(summary['missing_amounts_left'], 'missing amount')} "
                "empty, so they are ignored in totals and averages. "
                if summary["missing_amounts_left"] else ""
            )
            + (
                f"Removed {_format_count(summary['date_rows_removed'], 'row')} "
                "with unreadable dates."
                if summary["date_rows_removed"]
                else f"The app couldn't read {_format_count(summary['invalid_dates'], 'date')}; "
                "those rows are not included in the sales trend or date-related insights."
            )
        )

        if st.session_state.cleaning_report:
            with st.expander("View cleaning report"):
                st.text(st.session_state.cleaning_report)
            st.download_button(
                label="Download Cleaning Report",
                data=st.session_state.cleaning_report,
                file_name="cleaning_report.txt",
                mime="text/plain",
            )

    st.subheader("Cleaned Dataset Preview")
    cleaned_preview = df.head(10).copy()
    cleaned_preview["date"] = cleaned_preview["date"].map(
        lambda date: (
            format_display_date(date)
            if pd.notna(date)
            else "Not available"
        )
    )
    st.dataframe(
        cleaned_preview,
        use_container_width=True
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total sales",
        f"${kpis['total_sales']:.2f}"
    )

    col2.metric(
        "Average sale",
        f"${kpis['average_sale']:.2f}"
    )

    col3.metric(
        "Sales records",
        kpis["transaction_count"]
    )

    top_category = (
        category_df.iloc[0]["category"].title()
        if category_df["amount"].ne(0).any()
        else "No sales"
    )
    col4.metric(
        "Top sales category",
        top_category
    )

    invalid_date_rows = int(df["date"].isna().sum())
    if (df["amount"] < 0).any():
        st.info(
            "This file includes negative amounts. They reduce total sales "
            "and may represent refunds or returns."
        )
    if invalid_date_rows:
        st.info(
            f"The app couldn't read {invalid_date_rows} date(s). Those rows "
            "still count in the sales totals, but not in the sales trend "
            "or insights."
        )

    st.header(    "Sales by product category (dollars)")

    if category_df["amount"].ne(0).any():
        st.bar_chart(
            category_df.set_index("category")
        )
    else:
        st.info("There are no sales amounts to compare by category.")

    trend_df, trend_frequency = sales_by_time_period(df)

    if trend_df.empty:
        st.header("Sales Trend")
        st.info("No valid dates are available for a sales trend.")
    else:
        valid_dates = df["date"].dropna()
        date_min = valid_dates.min()
        date_max = valid_dates.max()
        frequency_labels = {
            "day": "Daily",
            "week": "Weekly",
            "month": "Monthly",
        }
        frequency_label = frequency_labels[trend_frequency]

        st.header(
            f"{frequency_label} sales: {format_display_date(date_min)} to "
            f"{format_display_date(date_max)}"
        )
        st.caption(
            f"Each point shows the total sales for one {trend_frequency}. "
            "The chart groups sales by day, week, or month based on the "
            "dates in your file."
        )

        if trend_df["amount"].ne(0).any():
            render_sales_trend(trend_df, trend_frequency)
        else:
            st.info("There are no sales amounts to show for this date range.")

    st.header("Share of total sales by category")

    distribution_df = category_distribution(df)

    if kpis["total_sales"] != 0:
        st.bar_chart(
            distribution_df.set_index("category")["percentage"].rename(
                "Share of sales (%)"
            )
        )
    else:
        st.info(
            "Category shares are unavailable because the sales total is zero."
        )
    distribution_display = distribution_df.rename(
        columns={
            "category": "Category",
            "amount": "Sales total ($)",
            "percentage": "Share of total (%)",
        }
    )
    st.dataframe(
        distribution_display,
        hide_index=True,
        use_container_width=True
    )

    # Download cleaned dataset

    csv_data = df.to_csv(index=False)

    st.download_button(
        label="Download Cleaned CSV",
        data=csv_data,
        file_name="cleaned_data.csv",
        mime="text/csv"
    )

    if st.button(
        "Continue to Insights"
    ):

        st.session_state.current_step = 4

        st.rerun()
        
# ==========================================
# STEP 4 - BUSINESS INSIGHTS
# ==========================================
#
# Purpose:
#     Convert analytical results into
#     human-readable business observations.
#
# Rather than displaying only charts and
# numbers, this stage explains what the
# results mean in plain language.
#
# Features:
#
#     - Business insights
#     - Revenue observations
#     - Category performance analysis
#     - Downloadable insight report
#     - Future placeholders for saving
#       and comparing analyses
#
# Data Source:
#     clean_df
#
# Output:
#     Human-readable business insights
#
# ==========================================

if st.session_state.current_step == 4:

    st.subheader(
        "Step 4 of 4"
    )

    st.title(
        "Your sales insights"
    )

    st.write(
        "These highlights summarize what the cleaned sales data shows."
    )

    # --------------------------------------
    # LOAD CLEAN DATASET
    # --------------------------------------
    #
    # Insights should always be generated
    # from the cleaned dataset created during
    # Step 2.
    #
    # This ensures insight generation uses
    # standardized, validated data.
    #
    # --------------------------------------

    df = st.session_state.clean_df

    invalid_date_rows = int(df["date"].isna().sum())
    if invalid_date_rows:
        st.info(
            f"The app couldn't read {invalid_date_rows} date(s). Those rows "
            "still count in the sales totals, but not in date-related insights."
        )

    # --------------------------------------
    # GENERATE INSIGHTS
    # --------------------------------------
    #
    # The insights module examines KPI
    # results and category performance in
    # order to create readable business
    # observations.
    #
    # Example:
    #
    #     Electronics generated the highest
    #     revenue.
    #
    #     2024-01-04 recorded the highest
    #     daily sales.
    #
    # --------------------------------------

    insights = generate_insights(df)

    # --------------------------------------
    # DISPLAY INSIGHTS
    # --------------------------------------
    #
    # Display each generated insight as a
    # separate bullet point.
    #
    # --------------------------------------

    st.header(
        "Key Findings"
    )

    for insight in insights:

        st.success(
            insight
        )

    # --------------------------------------
    # INSIGHT DOWNLOAD
    # --------------------------------------
    #
    # Convert all generated insights into a
    # downloadable report that can be shared
    # outside the application.
    #
    # --------------------------------------

    insight_text = "\n".join(insights)

    st.header(
        "Download your results"
    )

    st.download_button(
        label="Download sales highlights",
        data=insight_text,
        file_name="business_insights.txt",
        mime="text/plain"
    )

    # --------------------------------------
    # FUTURE FEATURES
    # --------------------------------------
    #
    # These buttons currently act as
    # placeholders for future functionality.
    #
    # Planned future features:
    #
    #     Save Analysis
    #     Compare Analyses
    #     Historical Dashboard Comparison
    #     Forecasting
    #
    # --------------------------------------

    st.caption(
        "Saving an analysis and comparing multiple files are not available yet."
    )

    # --------------------------------------
    # WORKFLOW COMPLETE
    # --------------------------------------
    #
    # Inform users that all workflow stages
    # have been completed successfully.
    #
    # --------------------------------------

    st.success(
        "Workflow complete. "
        "Business intelligence analysis "
        "has been generated successfully."
    )       
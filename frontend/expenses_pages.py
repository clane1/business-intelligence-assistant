"""Streamlit upload, review, dashboard, and insights pages for Expenses."""

import pandas as pd
import streamlit as st

from backend.cleaning_report import build_expenses_report
from backend.column_mapping import (
    ColumnMappingError,
    apply_mapping,
    suggest_expenses_mapping,
)
from backend.csv_loader import EXPENSES_COLUMNS, CsvFormatError, load_expenses_csv
from backend.expenses import (
    CleaningChoices,
    build_expenses_recommendations,
    clean_expenses,
    expenses_by_category,
    expenses_by_vendor,
    expenses_kpis,
    expense_trend,
    generate_expense_insights,
    spending_by_category,
)
from backend.recommendations import _preview, suggest_category_corrections
from backend.upload_diagnosis import diagnose_upload
from backend.validation import (
    count_currency_values,
    count_duplicates,
    count_invalid_dates,
    count_missing_amounts,
    invalid_amount_mask,
    validate_columns,
    validate_missing,
)
from frontend.charts import (
    format_cleaned_preview,
    format_display_date,
    render_expenses_trend,
)
from frontend.inventory_pages import dataset_type_selector, upload_widget_key

NOT_IN_FILE = "(not in my file)"
KEEP_DATES = "Keep expenses but exclude from trend"
REMOVE_DATE_ROWS = "Remove rows entirely"
APPLY_CORRECTION = "Apply correction"
KEEP_ORIGINAL = "Keep original value"
DELIMITERS = {"Comma": ",", "Tab": "\t", "Semicolon": ";"}


def _count(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def render_expenses_workflow() -> None:
    """Render the Expenses page for the active workflow step."""
    step = st.session_state.current_step
    if step == 1:
        _upload_page()
    elif step == 2:
        _check_page()
    elif step == 3:
        _dashboard_page()
    elif step == 4:
        _insights_page()


def _upload_page() -> None:
    st.subheader("Step 1 of 4")
    st.title("Upload your expenses data")
    st.write(
        "Choose an expenses CSV file. The app will check it and show any "
        "issues before cleaning."
    )
    dataset_type_selector()

    headers_included = st.checkbox(
        "The first row contains column names", value=True
    )
    if not headers_included:
        st.info(
            "Without a header row, columns must be in this order: "
            "date, amount, category, vendor."
        )
    delimiter = st.selectbox("What separates the columns?", list(DELIMITERS))
    uploaded_file = st.file_uploader(
        "Choose your expenses CSV file",
        type=["csv"],
        key=upload_widget_key("Expenses"),
    )
    upload_status = st.container()

    if uploaded_file is not None:
        try:
            df = load_expenses_csv(
                uploaded_file,
                delimiter=DELIMITERS[delimiter],
                headers_included=headers_included,
            )
        except CsvFormatError as error:
            upload_status.error(str(error))
        else:
            problem = diagnose_upload(
                df,
                DELIMITERS[delimiter],
                headers_included,
                label="expenses",
            )
            if problem:
                upload_status.warning(problem)
            else:
                st.session_state.raw_df = df
                st.session_state.source_df = df
                st.session_state.source_name = uploaded_file.name
                st.session_state.column_mapping = None
                st.session_state.cleaning_summary = None
                st.session_state.clean_df = None
                st.session_state.cleaning_report = None
                for key in list(st.session_state.keys()):
                    if key.startswith("map_"):
                        del st.session_state[key]
                upload_status.success("Dataset uploaded successfully.")
                if upload_status.button("Continue to data checks"):
                    st.session_state.current_step = 2
                    st.rerun()

    st.markdown("### Expenses data requirements")
    st.info(
        "Amounts may include dollar signs and commas. Use dates such as "
        "2024-01-31 when possible. Unreadable dates remain in expense totals "
        "but are excluded from the expense trend."
    )
    st.markdown(
        """
    ### Required columns

    | Column | Meaning | Example |
    |---|---|---|
    | `date` | Date the expense was recorded | 2024-01-01 |
    | `amount` | Expense amount | 25.48 |
    | `category` | Spending category | Office Supplies |
    | `vendor` | Supplier or merchant | Acme Office |
    """
    )
    st.markdown("### Example dataset")
    st.code(
        "date,amount,category,vendor\n"
        "2024-01-01,25.48,Office Supplies,Acme Office\n"
        "2024-01-02,15.99,Travel,City Transit\n"
        "2024-02-03,63.99,Software,Example Cloud\n"
    )


def _back_to_upload(key: str) -> None:
    if st.button("Back to Upload Data", key=key):
        st.session_state.current_step = 1
        st.rerun()


def _column_matching(missing: list[str]) -> None:
    source_df = st.session_state.source_df
    if source_df is None or not validate_columns(source_df, EXPENSES_COLUMNS):
        return

    mapping = st.session_state.column_mapping
    if mapping:
        st.caption(
            "Columns matched: "
            + ", ".join(
                f"{source} → {target}"
                for target, source in mapping.items()
                if source
            )
            + ". Other columns in your file are not used."
        )

    with st.expander(
        "Match your columns" if missing else "Change column matching",
        expanded=bool(missing),
    ):
        st.write(
            "Choose which column in your file provides each required value. "
            "Suggestions are filled in when a name looks similar."
        )
        suggestions = mapping or suggest_expenses_mapping(
            [str(column) for column in source_df.columns]
        )
        options = [NOT_IN_FILE] + [str(column) for column in source_df.columns]
        selected = {}
        for target in EXPENSES_COLUMNS:
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
            selected[target] = None if choice == NOT_IN_FILE else choice

        if st.button("Use these columns"):
            try:
                mapped = apply_mapping(
                    source_df.rename(columns=str),
                    selected,
                    EXPENSES_COLUMNS,
                )
            except ColumnMappingError as error:
                st.error(str(error))
            else:
                st.session_state.raw_df = mapped
                st.session_state.column_mapping = selected
                for key in list(st.session_state.keys()):
                    if key.startswith(("exp_", "fix_category_")):
                        del st.session_state[key]
                st.rerun()


def _recommendation_cards(
    df: pd.DataFrame,
) -> tuple[CleaningChoices, bool]:
    st.divider()
    st.header("Recommended actions")
    recommendations = build_expenses_recommendations(df)
    corrections = suggest_category_corrections(df)
    no_fixes = not recommendations and not corrections
    if no_fixes:
        st.success(
            "No fixes are needed for duplicates, missing amounts, dates, "
            "or category spelling."
        )

    choices = {
        "remove_duplicates": False,
        "fill_missing_amounts": False,
        "remove_invalid_date_rows": False,
    }
    accepted_corrections = {}

    if corrections:
        with st.container(border=True):
            st.subheader(f"{_count(len(corrections), 'possible category typo')} found")
            for correction in corrections:
                st.markdown(
                    f"**{correction.original} → {correction.suggestion}** "
                    f"({_count(correction.count, 'row')})"
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
                    accepted_corrections[correction.original] = correction.suggestion

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
                choices["remove_duplicates"] = st.checkbox(
                    "Remove duplicates",
                    value=True,
                    key="exp_fix_duplicates",
                )
            elif recommendation.key == "missing_amounts":
                choices["fill_missing_amounts"] = st.checkbox(
                    "Apply fix",
                    value=True,
                    key="exp_fix_missing_amounts",
                )
            elif recommendation.key == "invalid_dates":
                date_choice = st.radio(
                    "How should these rows be handled?",
                    [KEEP_DATES, REMOVE_DATE_ROWS],
                    key="exp_invalid_date_handling",
                )
                choices["remove_invalid_date_rows"] = (
                    date_choice == REMOVE_DATE_ROWS
                )

    return (
        CleaningChoices(
            **choices,
            category_corrections=accepted_corrections,
        ),
        no_fixes,
    )


def _check_page() -> None:
    st.subheader("Step 2 of 4")
    st.title("Check your expenses data")
    df = st.session_state.raw_df
    missing_columns = validate_columns(df, EXPENSES_COLUMNS)

    st.header("Data summary")
    st.subheader("Dataset Preview")
    st.dataframe(df.head(10), width="stretch")
    st.write(f"{len(df)} rows and {len(df.columns)} columns")

    if missing_columns:
        st.error(
            "Your file is missing required "
            + (
                f"{missing_columns[0]} column."
                if len(missing_columns) == 1
                else f"columns: {', '.join(missing_columns)}."
            )
        )
        _back_to_upload("exp_back_missing")
    else:
        st.success("Your file has all the columns needed for expense analysis.")

    _column_matching(missing_columns)

    st.divider()
    st.header("Data quality metrics")
    amounts_missing = count_missing_amounts(df)
    duplicates = count_duplicates(df)
    dates_invalid = count_invalid_dates(df) if "date" in df.columns else 0
    metrics = st.columns(4)
    metrics[0].metric("Rows in file", len(df))
    metrics[1].metric("Empty cells", int(validate_missing(df).sum()))
    metrics[2].metric("Missing amounts", amounts_missing)
    metrics[3].metric("Repeated rows", duplicates)

    st.subheader("Empty cells by column")
    st.dataframe(validate_missing(df).rename("Empty cells").to_frame())

    problems = {}
    if not missing_columns and "amount" in df.columns:
        amount_mask = invalid_amount_mask(df)
        if amount_mask.any():
            problems["amount"] = amount_mask
            st.error(
                f"{int(amount_mask.sum())} value(s) in the amount column "
                "aren't numbers and can't be cleaned automatically: "
                f"{_preview(df, amount_mask, 'amount')}."
            )
            st.markdown(
                "**How to fix this:** correct the non-numeric amount values "
                "in the source CSV, then upload the corrected file."
            )
            _back_to_upload("exp_back_amounts")
        elif count_currency_values(df):
            st.info("Dollar signs and commas in amounts are removed during cleaning.")

    if dates_invalid and not missing_columns:
        st.info(
            f"{_count(dates_invalid, 'date')} couldn't be read. Those rows "
            "remain in expense totals but are excluded from the trend."
        )
    cleaning_blocked = bool(missing_columns or problems)

    choices = CleaningChoices()
    no_fixes = False
    if not missing_columns:
        choices, no_fixes = _recommendation_cards(df)

    if cleaning_blocked:
        st.header("Apply fixes")
        st.warning(
            "Cleaning is unavailable until required columns and numeric "
            "amount values are corrected in the source file."
        )
        button_label = "Apply selected fixes and view dashboard"
    elif no_fixes:
        st.header("Continue")
        st.write(
            "Routine formatting is applied to a copy of the data. "
            "The uploaded file is not changed."
        )
        button_label = "Continue to dashboard"
    else:
        st.header("Apply fixes")
        st.write("Your choices are applied to a copy of the uploaded data.")
        button_label = "Apply selected fixes and view dashboard"

    if st.button(button_label, disabled=cleaning_blocked):
        cleaned, summary = clean_expenses(df, choices)
        if cleaned.empty:
            st.error(
                "No rows remain after cleaning. Add category values to the "
                "file and upload the corrected CSV."
            )
            return
        st.session_state.clean_df = cleaned
        st.session_state.cleaning_summary = summary
        st.session_state.cleaning_report = build_expenses_report(
            summary,
            source_name=st.session_state.source_name,
            column_mapping=st.session_state.column_mapping,
        )
        st.session_state.current_step = 3
        st.rerun()


def _dashboard_page() -> None:
    st.subheader("Step 3 of 4")
    st.title("Expenses dashboard")
    df = st.session_state.clean_df
    summary = st.session_state.cleaning_summary

    if summary:
        st.subheader("What the app changed")
        st.success(
            f"Kept {summary['rows_after']} of {summary['rows_before']} rows. "
            f"Removed {_count(summary['duplicates_removed'], 'duplicate row')} "
            f"and {_count(summary['category_rows_removed'], 'row')} with "
            "blank categories. "
            f"Filled {summary['missing_amounts_filled']} missing amount(s)."
        )
        with st.expander("View cleaning report"):
            st.text(st.session_state.cleaning_report)
        st.download_button(
            "Download Cleaning Report",
            st.session_state.cleaning_report,
            file_name="expenses_cleaning_report.txt",
            mime="text/plain",
        )

    st.subheader("Cleaned Dataset Preview")
    st.dataframe(format_cleaned_preview(df), width="stretch")

    kpis = expenses_kpis(df)
    cards = st.columns(4)
    cards[0].metric("Total expenses", f"${kpis['total_expenses']:,.2f}")
    cards[1].metric("Average expense", f"${kpis['average_expense']:,.2f}")
    cards[2].metric("Expense records", kpis["expense_records"])
    cards[3].metric(
        "Largest expense category",
        kpis["largest_expense_category"] or "No expenses",
    )

    invalid_dates = int(df["date"].isna().sum())
    if invalid_dates:
        st.info(
            f"{_count(invalid_dates, 'date')} couldn't be read. These "
            "expenses count in totals but not the trend."
        )

    by_category = expenses_by_category(df)
    st.header("Expenses by Category")
    if by_category["amount"].gt(0).any():
        st.bar_chart(by_category.set_index("category")["amount"])
    else:
        st.info("There are no positive expenses to compare by category.")

    trend, frequency = expense_trend(df)
    st.header("Expense Trend")
    if trend.empty:
        st.info("No readable dates are available for an expense trend.")
    elif trend["amount"].gt(0).any():
        first_date = df["date"].dropna().min()
        last_date = df["date"].dropna().max()
        st.caption(
            f"Expenses are grouped by {frequency} from "
            f"{format_display_date(first_date)} to "
            f"{format_display_date(last_date)}."
        )
        render_expenses_trend(trend, frequency)
    else:
        st.info("There are no positive expenses to show over time.")

    distribution = spending_by_category(df)
    st.header("Percent of Spending by Category")
    if kpis["total_expenses"] > 0:
        st.bar_chart(
            distribution.set_index("category")["percentage"].rename(
                "Share of expenses (%)"
            )
        )
        st.dataframe(
            distribution.rename(
                columns={
                    "category": "Category",
                    "amount": "Expenses ($)",
                    "percentage": "Share of expenses (%)",
                }
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Category spending shares are unavailable because total expenses are zero.")

    by_vendor = expenses_by_vendor(df)
    st.header("Expenses by Vendor")
    if not by_vendor.empty and by_vendor["amount"].gt(0).any():
        st.bar_chart(by_vendor.set_index("vendor")["amount"])
    else:
        st.info("There are no vendor expenses to rank.")

    st.download_button(
        "Download Cleaned CSV",
        df.to_csv(index=False),
        file_name="cleaned_expenses.csv",
        mime="text/csv",
    )
    if st.button("Continue to Insights"):
        st.session_state.current_step = 4
        st.rerun()


def _insights_page() -> None:
    st.subheader("Step 4 of 4")
    st.title("Your expenses insights")
    st.write("These highlights summarize spending in the cleaned data.")
    insights = generate_expense_insights(st.session_state.clean_df)

    st.header("Key Findings")
    for insight in insights:
        st.success(insight)

    st.header("Download your results")
    st.download_button(
        "Download expense highlights",
        "\n".join(insights),
        file_name="expense_insights.txt",
        mime="text/plain",
    )
    st.caption(
        "Saving an analysis and comparing multiple files are not available yet."
    )
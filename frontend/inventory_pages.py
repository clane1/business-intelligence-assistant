"""Streamlit pages for the Inventory dataset type.

``streamlit_app_v2.py`` hands control to :func:`render_inventory_workflow` when
the user selects the Inventory dataset type. The four steps (upload, check,
dashboard, insights) mirror the Sales workflow and share its session state
keys, so the sidebar and "Start New Analysis" work unchanged. The sales code
path is not touched by this module.
"""

import pandas as pd
import streamlit as st

from backend.cleaning_report import build_inventory_report
from backend.column_mapping import (
    INVENTORY_OPTIONAL_COLUMNS,
    ColumnMappingError,
    apply_mapping,
    suggest_inventory_mapping,
)
from backend.csv_loader import INVENTORY_COLUMNS, CsvFormatError, load_inventory_csv
from backend.inventory import (
    InventoryChoices,
    blocking_problems,
    build_inventory_recommendations,
    clean_inventory,
    count_currency_symbols,
    count_missing,
    count_negative,
    count_unreadable_reorder_levels,
    generate_inventory_insights,
    inventory_kpis,
    low_stock_rows,
    top_value_items,
    units_by_category,
    value_by_category,
)
from backend.recommendations import _preview, suggest_category_corrections
from backend.upload_diagnosis import diagnose_upload
from backend.validation import count_duplicates, validate_columns, validate_missing

DATASET_TYPES = ["Sales", "Inventory"]
NOT_IN_FILE = "(not in my file)"
APPLY_CORRECTION = "Apply correction"
KEEP_ORIGINAL = "Keep original value"
KEEP_NEGATIVES = "Keep these rows (they reduce totals)"
REMOVE_NEGATIVES = "Remove these rows"

# Widget keys that belong to a dataset's review forms; cleared on a type switch.
_WIDGET_PREFIXES = ("fix_", "map_", "inv_", "invalid_date_handling")
_DATA_KEYS = (
    "raw_df", "clean_df", "cleaning_summary", "source_df", "source_name",
    "cleaning_report", "column_mapping",
)
_DELIMITERS = {"Comma": ",", "Tab": "\t", "Semicolon": ";"}


def _count(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _noun(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _units(value: float) -> str:
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


def _on_type_change() -> None:
    """Start over with the newly selected dataset type."""
    st.session_state.dataset_type = st.session_state.dataset_type_choice
    st.session_state.current_step = 1
    for key in _DATA_KEYS:
        st.session_state[key] = None
    for key in list(st.session_state.keys()):
        if key.startswith(_WIDGET_PREFIXES):
            del st.session_state[key]


def dataset_type_selector() -> None:
    """Show the dataset type dropdown; changing it resets the analysis."""
    st.selectbox(
        "Dataset type",
        DATASET_TYPES,
        index=DATASET_TYPES.index(st.session_state.dataset_type),
        key="dataset_type_choice",
        on_change=_on_type_change,
        help="Changing this clears the current upload so the two kinds of "
        "data are never mixed.",
    )


def render_inventory_workflow() -> None:
    """Render the Inventory page for the current workflow step."""
    step = st.session_state.current_step
    if step == 1:
        _upload_page()
    elif step == 2:
        _check_page()
    elif step == 3:
        _dashboard_page()
    elif step == 4:
        _insights_page()


# ----------------------------------------------------------------------
# Step 1 - upload
# ----------------------------------------------------------------------

def _upload_page() -> None:
    st.subheader("Step 1 of 4")
    st.title("Upload your inventory data")
    st.write(
        "Choose an inventory CSV file. The app will check it and show any "
        "issues before cleaning the data."
    )
    dataset_type_selector()

    headers_included = st.checkbox(
        "The first row contains column names", value=True
    )
    if not headers_included:
        st.info(
            "Without a header row, columns must be in this order: "
            "item, category, quantity, unit_cost. Optional columns "
            "(reorder_level, last_updated) need a header row."
        )

    delimiter = st.selectbox(
        "What separates the columns?", list(_DELIMITERS)
    )
    uploaded_file = st.file_uploader(
        "Choose your inventory CSV file", type=["csv"], key="upload_Inventory"
    )
    upload_status = st.container()

    if uploaded_file is not None:
        try:
            df = load_inventory_csv(
                uploaded_file,
                delimiter=_DELIMITERS[delimiter],
                headers_included=headers_included,
            )
        except CsvFormatError as error:
            upload_status.error(str(error))
        else:
            problem = diagnose_upload(
                df, _DELIMITERS[delimiter], headers_included, label="inventory"
            )
            if problem:
                upload_status.warning(problem)
            else:
                st.session_state.raw_df = df
                st.session_state.source_df = df
                st.session_state.source_name = uploaded_file.name
                st.session_state.column_mapping = None
                st.session_state.cleaning_summary = None
                for key in list(st.session_state.keys()):
                    if key.startswith("map_"):
                        del st.session_state[key]
                upload_status.success("Dataset uploaded successfully.")
                if upload_status.button("Continue to data checks"):
                    st.session_state.current_step = 2
                    st.rerun()

    st.markdown("### Inventory data requirements")
    st.info(
        "Quantities are the number of units in stock. Unit costs may include "
        "dollar signs and commas. Inventory value is calculated as quantity "
        "× unit cost. Negative numbers are not changed automatically; the "
        "app asks you to review them."
    )
    st.markdown(
        """
    ### Columns your file needs

    | Column name | What it means | Example |
    |----------|----------|----------|
    | `item` | Product name | Laptop |
    | `category` | Product category | Electronics |
    | `quantity` | Units in stock | 12 |
    | `unit_cost` | Cost of one unit | 899.99 |

    ### Optional columns

    | Column name | What it means | Example |
    |----------|----------|----------|
    | `reorder_level` | Restock when quantity falls to this number | 5 |
    | `last_updated` | When the stock was last counted | 2024-03-01 |

    With a `reorder_level` column, the dashboard also reports low-stock items.
    """
    )
    st.markdown("### Example dataset")
    st.code(
        "item,category,quantity,unit_cost,reorder_level\n"
        "Laptop,Electronics,12,899.99,5\n"
        "Jacket,Clothing,40,59.00,10\n"
        "Stapler,Office,70,4.25,25\n"
        "Coffee Beans,Food,200,8.40,80\n"
    )


# ----------------------------------------------------------------------
# Step 2 - check and review recommended actions
# ----------------------------------------------------------------------

def _back_to_upload(key: str) -> None:
    if st.button("Back to Upload Data", key=key):
        st.session_state.current_step = 1
        st.rerun()


def _column_matching(df: pd.DataFrame, missing_columns: list) -> None:
    """Let the user match their own headers to the inventory columns."""
    source_df = st.session_state.source_df
    if source_df is None or not validate_columns(source_df, INVENTORY_COLUMNS):
        return

    applied = st.session_state.column_mapping
    if applied:
        st.caption(
            "Columns matched: "
            + ", ".join(
                f"{source} → {target}"
                for target, source in applied.items()
                if source
            )
            + ". Other columns in your file are not used."
        )

    with st.expander(
        "Match your columns" if missing_columns else "Change column matching",
        expanded=bool(missing_columns),
    ):
        st.write(
            "Choose which column in your file provides each value the app "
            "needs. Suggestions are filled in where a name looks similar. "
            "Optional columns can be left as not in my file."
        )
        suggestions = applied or suggest_inventory_mapping(
            list(source_df.columns)
        )
        options = [NOT_IN_FILE] + [str(c) for c in source_df.columns]
        chosen = {}
        for target in INVENTORY_COLUMNS + INVENTORY_OPTIONAL_COLUMNS:
            suggested = suggestions.get(target)
            default = (
                options.index(str(suggested))
                if suggested is not None and str(suggested) in options
                else 0
            )
            optional = target in INVENTORY_OPTIONAL_COLUMNS
            choice = st.selectbox(
                f"{target.replace('_', ' ').capitalize()} column"
                + (" (optional)" if optional else ""),
                options,
                index=default,
                key=f"map_{target}",
            )
            chosen[target] = None if choice == NOT_IN_FILE else choice

        if st.button("Use these columns"):
            try:
                st.session_state.raw_df = apply_mapping(
                    source_df.rename(columns=str),
                    chosen,
                    INVENTORY_COLUMNS,
                    INVENTORY_OPTIONAL_COLUMNS,
                )
            except ColumnMappingError as error:
                st.error(str(error))
            else:
                st.session_state.column_mapping = chosen
                for key in list(st.session_state.keys()):
                    if key.startswith(("inv_", "fix_category_")):
                        del st.session_state[key]
                st.rerun()


def _check_page() -> None:
    st.subheader("Step 2 of 4")
    st.title("Check your data")

    df = st.session_state.raw_df
    missing_columns = validate_columns(df, INVENTORY_COLUMNS)

    st.header("Data summary")
    st.subheader("Dataset Preview")
    st.dataframe(df.head(10), use_container_width=True)
    st.subheader("Your file at a glance")
    st.write(f"{len(df)} rows and {len(df.columns)} columns")

    if missing_columns:
        st.error(
            "Your file is missing the required "
            + (
                f"{missing_columns[0]} column."
                if len(missing_columns) == 1
                else f"columns: {', '.join(missing_columns)}."
            )
        )
        if len(df.columns) == 1:
            st.warning(
                "Only one column was read, so the file's separator probably "
                "doesn't match the **What separates the columns?** setting."
            )
        st.markdown(
            "**How to fix this**\n\n"
            "1. If your file uses different names for these values (for "
            "example *Qty on Hand* instead of *quantity*), match them in the "
            "**Match your columns** form below.\n"
            "2. If the preview above looks wrong (everything in one column, "
            "or the first row is data), click **Back to Upload Data**, "
            "change the **separator** or **first row contains column "
            "names** setting, and choose your file again.\n"
            "3. If a required column really isn't in your file, add it in "
            "your spreadsheet, save as CSV, click **Back to Upload Data**, "
            "and choose the corrected file."
        )
        _back_to_upload("back_missing")
    else:
        st.success("Your file has all the columns needed for inventory analysis.")

    _column_matching(df, missing_columns)

    st.divider()
    st.header("Data quality metrics")
    duplicates = count_duplicates(df)
    missing_quantity = count_missing(df, "quantity")
    missing_cost = count_missing(df, "unit_cost")
    negative_quantity = count_negative(df, "quantity")
    negative_cost = count_negative(df, "unit_cost")

    columns = st.columns(5)
    columns[0].metric("Rows in file", len(df))
    columns[1].metric("Empty cells", int(validate_missing(df).sum()))
    columns[2].metric("Missing quantities", missing_quantity)
    columns[3].metric("Missing unit costs", missing_cost)
    columns[4].metric("Repeated rows", duplicates)

    if missing_columns:
        st.info("Some checks aren't available until you add all required columns.")
    else:
        st.info(
            f"Your file has {_count(duplicates, 'repeated row')}, "
            f"{_noun(missing_quantity, 'missing quantity', 'missing quantities')}, "
            f"{_count(missing_cost, 'missing unit cost')}, "
            f"{_noun(negative_quantity, 'negative quantity', 'negative quantities')} and "
            f"{_count(negative_cost, 'negative unit cost')}. Review the "
            "recommended actions below; nothing changes until you apply them."
        )
        unreadable = count_unreadable_reorder_levels(df)
        if unreadable:
            st.info(
                f"{_count(unreadable, 'reorder level')} couldn't be read as "
                "numbers and will be ignored when finding low-stock items."
            )

    st.subheader("Empty cells by column")
    st.dataframe(validate_missing(df).rename("Empty cells").to_frame())

    st.subheader("Check the quantity and unit cost format")
    problems = {} if missing_columns else blocking_problems(df)
    if missing_columns:
        st.info("Number checks are unavailable until the required columns are present.")
    elif problems:
        for column, mask in problems.items():
            st.error(
                f"{int(mask.sum())} value(s) in the {column} column aren't "
                "numbers and can't be cleaned automatically. These rows need "
                f"correcting: {_preview(df, mask, column)}."
            )
        st.markdown(
            "**How to fix this:** open your file in a spreadsheet, replace "
            "or delete those values (row numbers count data rows, not the "
            "header), save it as CSV, click **Back to Upload Data**, and "
            "choose the corrected file."
        )
        _back_to_upload("back_numbers")
    elif count_currency_symbols(df):
        st.info(
            "Some unit costs include dollar signs or commas. The app will "
            "remove those when it cleans the data."
        )
    else:
        st.success("Quantities and unit costs look ready to use.")

    choices = InventoryChoices()
    no_fixes_needed = False
    cleaning_blocked = bool(missing_columns or problems)

    if not missing_columns:
        choices, no_fixes_needed = _recommended_actions(df)

    st.divider()
    if cleaning_blocked:
        st.header("Apply fixes")
        st.warning(
            "Cleaning is unavailable until the problem above is fixed: "
            + (
                "a required column is missing."
                if missing_columns
                else "some quantities or unit costs aren't numbers."
            )
            + " Fix it in your file and upload it again."
        )
        apply_label = "Apply selected fixes and view dashboard"
    elif no_fixes_needed:
        st.header("Continue")
        st.write(
            "There's nothing to review. Routine formatting, such as removing "
            "dollar signs and standardizing category capitalization, is "
            "still applied to a copy of your data. Your uploaded file is not "
            "changed."
        )
        apply_label = "Continue to dashboard"
    else:
        st.header("Apply fixes")
        st.write(
            "Your choices above are applied to a copy of your data. Your "
            "uploaded file is not changed."
        )
        apply_label = "Apply selected fixes and view dashboard"

    if st.button(apply_label, disabled=cleaning_blocked):
        cleaned, summary = clean_inventory(df, choices)
        if cleaned.empty:
            st.error(
                "No rows remain after cleaning. Rows are removed when they "
                "have a blank category (or when you chose to remove them). "
                "Fix your file, go back to Upload Data, and choose it again."
            )
        else:
            st.session_state.clean_df = cleaned
            st.session_state.cleaning_summary = summary
            st.session_state.cleaning_report = build_inventory_report(
                summary,
                source_name=st.session_state.source_name,
                column_mapping=st.session_state.column_mapping,
            )
            st.session_state.current_step = 3
            st.rerun()


def _recommendation_card(recommendation, choice_values: dict) -> None:
    """Show one recommendation card and record the user's choice."""
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

        key = recommendation.key
        if key == "duplicates":
            choice_values["remove_duplicates"] = st.checkbox(
                "Remove duplicates", value=True, key="inv_fix_duplicates"
            )
        elif key == "missing_quantity":
            choice_values["fill_missing_quantity"] = st.checkbox(
                "Apply fix", value=True, key="inv_fix_missing_quantity"
            )
        elif key == "missing_unit_cost":
            choice_values["fill_missing_unit_cost"] = st.checkbox(
                "Apply fix", value=True, key="inv_fix_missing_unit_cost"
            )
        elif key in ("negative_quantity", "negative_unit_cost"):
            decision = st.radio(
                "How should these rows be handled?",
                [KEEP_NEGATIVES, REMOVE_NEGATIVES],
                key=f"inv_{key}",
            )
            choice_values[f"remove_{key}_rows"] = decision == REMOVE_NEGATIVES


def _recommended_actions(df: pd.DataFrame) -> tuple[InventoryChoices, bool]:
    """Show the recommendation cards; return the user's choices and whether none were needed."""
    st.divider()
    st.header("Recommended actions")
    recommendations = build_inventory_recommendations(df)
    corrections = suggest_category_corrections(df)

    no_fixes_needed = not recommendations and not corrections
    if no_fixes_needed:
        st.success(
            "No fixes are needed for duplicates, missing values, negative "
            "numbers, or category spelling."
        )

    choice_values = {
        "remove_duplicates": False,
        "fill_missing_quantity": False,
        "fill_missing_unit_cost": False,
        "remove_negative_quantity_rows": False,
        "remove_negative_unit_cost_rows": False,
    }
    accepted = {}

    if corrections:
        with st.container(border=True):
            st.subheader(
                f"{_count(len(corrections), 'possible category misspelling')} found"
            )
            st.markdown(
                "**Suggested fix:** Rename uncommon spellings to the similar "
                "category used more often"
            )
            st.markdown(
                "**Impact:** Inventory is grouped under the corrected "
                "category in charts and insights."
            )
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
                    accepted[correction.original] = correction.suggestion

    for recommendation in recommendations:
        _recommendation_card(recommendation, choice_values)

    return (
        InventoryChoices(**choice_values, category_corrections=accepted),
        no_fixes_needed,
    )


# ----------------------------------------------------------------------
# Step 3 - dashboard
# ----------------------------------------------------------------------

def _dashboard_page() -> None:
    st.subheader("Step 3 of 4")
    st.title("Inventory dashboard")

    df = st.session_state.clean_df
    summary = st.session_state.cleaning_summary

    if summary:
        st.subheader("What the app changed")
        st.success(
            f"Kept {summary['rows_after']} of {summary['rows_before']} rows. "
            f"Removed {_count(summary['duplicates_removed'], 'repeated row')} "
            f"and {_count(summary['category_rows_removed'], 'row')} with a "
            "blank category. "
            + (
                f"Removed {_count(summary['negative_rows_removed'], 'row')} "
                "with negative values. "
                if summary["negative_rows_removed"] else ""
            )
            + (
                f"Corrected the spelling of "
                f"{_count(summary['categories_corrected'], 'category row')}. "
                if summary["categories_corrected"] else ""
            )
            + (
                f"Replaced {summary['missing_quantity_filled']} missing "
                "quantity value(s) with 0. "
                if summary["missing_quantity_filled"] else ""
            )
            + (
                f"Replaced {summary['missing_unit_cost_filled']} missing "
                "unit cost value(s) with 0."
                if summary["missing_unit_cost_filled"] else ""
            )
        )
        if st.session_state.cleaning_report:
            with st.expander("View cleaning report"):
                st.text(st.session_state.cleaning_report)
            st.download_button(
                label="Download Cleaning Report",
                data=st.session_state.cleaning_report,
                file_name="inventory_cleaning_report.txt",
                mime="text/plain",
            )

    st.subheader("Cleaned Dataset Preview")
    st.dataframe(df.head(10), use_container_width=True)

    kpis = inventory_kpis(df)
    columns = st.columns(4)
    columns[0].metric("Total inventory value", f"${kpis['total_value']:,.2f}")
    columns[1].metric("Total units", _units(kpis["total_units"]))
    columns[2].metric("Unique items", kpis["unique_items"])
    columns[3].metric(
        "Top inventory category", kpis["top_category"] or "No inventory value"
    )

    if (pd.to_numeric(df["quantity"], errors="coerce") < 0).any() or (
        pd.to_numeric(df["unit_cost"], errors="coerce") < 0
    ).any():
        st.info(
            "This file includes negative quantities or unit costs. They "
            "reduce the totals below."
        )

    if "reorder_level" in df.columns:
        low = low_stock_rows(df)
        if low.empty:
            st.success("No items are at or below their reorder level.")
        else:
            st.warning(
                f"{summary['low_stock_items'] if summary else len(low)} Low "
                "Stock Items Detected (quantity at or below reorder level)."
            )
            with st.expander("Show low stock items"):
                st.dataframe(low, hide_index=True, use_container_width=True)

    st.header("Inventory value by category (dollars)")
    by_value = value_by_category(df)
    if by_value["value"].ne(0).any():
        st.bar_chart(by_value.set_index("category"))
    else:
        st.info("There is no inventory value to compare by category.")

    st.header("Units in stock by category")
    by_units = units_by_category(df)
    if by_units["quantity"].ne(0).any():
        st.bar_chart(by_units.set_index("category"))
    else:
        st.info("There are no units in stock to compare by category.")

    st.header("Highest value items")
    st.caption("Top 10 items by quantity × unit cost: where inventory money is tied up.")
    top_items = top_value_items(df)
    if not top_items.empty and top_items["value"].ne(0).any():
        st.bar_chart(top_items.set_index("item"))
    else:
        st.info("No items have an inventory value to rank.")

    st.download_button(
        label="Download Cleaned CSV",
        data=df.to_csv(index=False),
        file_name="cleaned_inventory.csv",
        mime="text/csv",
    )
    if st.button("Continue to Insights"):
        st.session_state.current_step = 4
        st.rerun()


# ----------------------------------------------------------------------
# Step 4 - insights
# ----------------------------------------------------------------------

def _insights_page() -> None:
    st.subheader("Step 4 of 4")
    st.title("Your inventory insights")
    st.write("These highlights summarize what the cleaned inventory data shows.")

    insights = generate_inventory_insights(st.session_state.clean_df)

    st.header("Key Findings")
    for insight in insights:
        st.success(insight)

    st.header("Download your results")
    st.download_button(
        label="Download inventory highlights",
        data="\n".join(insights),
        file_name="inventory_insights.txt",
        mime="text/plain",
    )
    st.caption(
        "Saving an analysis and comparing multiple files are not available yet."
    )
    st.success(
        "Workflow complete. Business intelligence analysis has been "
        "generated successfully."
    )

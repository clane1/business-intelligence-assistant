"""Shared chart rendering helpers for the Streamlit frontends."""

import altair as alt
import pandas as pd
import streamlit as st

from backend.forecasting import generate_forecast_insight


def format_display_date(value: pd.Timestamp) -> str:
    """Format a timestamp as a full month name, unpadded day, and full year.

    Args:
        value: Timestamp to present in the interface.

    Returns:
        A label such as ``January 2, 2024``.
    """
    return f"{value:%B} {value.day}, {value.year}"


def format_cleaned_preview(df: pd.DataFrame) -> pd.DataFrame:
    """Return a display copy with parsed dates shown without midnight times."""
    preview = df.head(10).copy()
    if "date" in preview.columns:
        preview["date"] = preview["date"].map(
            lambda value: (
                format_display_date(pd.Timestamp(value))
                if pd.notna(value)
                else "Not available"
            )
        )
    return preview


def build_time_trend_chart(
    trend_df: pd.DataFrame,
    frequency: str,
    value_label: str,
) -> alt.Chart:
    """Build a chronological trend chart with explicit period labels.

    Daily and weekly periods use month/day/year labels; monthly periods use
    abbreviated month/year labels. The chart retains every data point while
    reducing the number of displayed axis labels for long non-monthly trends.

    Args:
        trend_df: DataFrame with aggregated ``date`` and ``amount`` columns.
        frequency: One of ``day``, ``week``, or ``month``.

    Returns:
        An Altair line chart with tooltips and explicitly ordered labels.
    """
    dates = trend_df["date"]
    if frequency == "month":
        period_labels = dates.map(lambda date: f"{date:%b} {date.year}")
        tooltip_periods = dates.map(lambda date: f"{date:%B} {date.year}")
    else:
        period_labels = dates.map(
            lambda date: f"{date:%b} {date.day}, {date.year}"
        )
        tooltip_periods = dates.map(format_display_date)
    chart_df = trend_df.assign(
        period=period_labels,
        tooltip_period=tooltip_periods,
    )
    period_order = chart_df["period"].tolist()
    label_step = (
        1
        if frequency == "month"
        else max(1, (len(period_order) + 9) // 10)
    )
    axis_values = period_order[::label_step]
    if period_order and axis_values[-1] != period_order[-1]:
        axis_values.append(period_order[-1])
    tooltip_title = {
        "day": "Date",
        "week": "Week starting",
        "month": "Month",
    }[frequency]

    return (
        alt.Chart(chart_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "period:N",
                sort=period_order,
                axis=alt.Axis(
                    title=None,
                    labelAngle=-45,
                    values=axis_values,
                ),
            ),
            y=alt.Y("amount:Q", title=value_label),
            tooltip=[
                alt.Tooltip(
                    "tooltip_period:N",
                    title=tooltip_title,
                ),
                alt.Tooltip(
                    "amount:Q",
                    title=value_label,
                    format="$,.2f",
                ),
            ],
        )
    )


def build_sales_trend_chart(
    trend_df: pd.DataFrame,
    frequency: str,
) -> alt.Chart:
    """Build the Sales-specific time-trend chart."""
    return build_time_trend_chart(trend_df, frequency, "Sales")


def build_expenses_trend_chart(
    trend_df: pd.DataFrame,
    frequency: str,
) -> alt.Chart:
    """Build the Expenses-specific time-trend chart."""
    return build_time_trend_chart(trend_df, frequency, "Expenses")


def build_sales_forecast_chart(forecast_df: pd.DataFrame) -> alt.Chart:
    """Plot observed daily sales and future predictions with distinct colors."""
    chart_data = forecast_df.melt(
        id_vars="date",
        value_vars=["historical_sales", "forecast_sales"],
        var_name="series",
        value_name="sales",
    ).dropna(subset=["sales"])
    chart_data["series"] = chart_data["series"].map({
        "historical_sales": "Historical",
        "forecast_sales": "Forecast",
    })
    return (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("sales:Q", title="Daily sales ($)"),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(
                    domain=["Historical", "Forecast"],
                    range=["#1f77b4", "#ff7f0e"],
                ),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("sales:Q", title="Daily sales", format="$,.2f"),
            ],
        )
    )


def render_sales_forecast(forecast_df: pd.DataFrame) -> None:
    """Render the Sales forecast or its insufficient-data message."""
    st.header("Forecast")
    if forecast_df.empty:
        st.info(generate_forecast_insight(forecast_df))
        return
    st.caption(
        "Daily sales projected for 30 days using a linear trend. "
        "Only recorded dates with amounts are used; missing days are not "
        "assumed to have zero sales. Projections are estimates, not guarantees."
    )
    st.altair_chart(
        build_sales_forecast_chart(forecast_df),
        width="stretch",
        alt="Historical daily sales and 30-day sales forecast",
    )
    st.info(generate_forecast_insight(forecast_df))


def render_sales_trend(
    trend_df: pd.DataFrame,
    frequency: str,
) -> None:
    """Render an Altair trend chart in the current Streamlit page.

    Args:
        trend_df: DataFrame with aggregated ``date`` and ``amount`` columns.
        frequency: One of ``day``, ``week``, or ``month``.
    """
    chart = build_sales_trend_chart(trend_df, frequency)
    st.altair_chart(chart, width="stretch")


def render_expenses_trend(
    trend_df: pd.DataFrame,
    frequency: str,
) -> None:
    """Render the Expenses time-trend chart."""
    chart = build_expenses_trend_chart(trend_df, frequency)
    st.altair_chart(chart, width="stretch")

"""Shared chart rendering helpers for the Streamlit frontends."""

import altair as alt
import pandas as pd
import streamlit as st


def format_display_date(value: pd.Timestamp) -> str:
    """Format a timestamp as a full month name, unpadded day, and full year.

    Args:
        value: Timestamp to present in the interface.

    Returns:
        A label such as ``January 2, 2024``.
    """
    return f"{value:%B} {value.day}, {value.year}"


def build_sales_trend_chart(
    trend_df: pd.DataFrame,
    frequency: str,
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
            y=alt.Y("amount:Q", title="Sales"),
            tooltip=[
                alt.Tooltip(
                    "tooltip_period:N",
                    title=tooltip_title,
                ),
                alt.Tooltip("amount:Q", title="Sales", format="$,.2f"),
            ],
        )
    )


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

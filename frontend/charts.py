"""Shared chart rendering helpers for the Streamlit frontends."""

import altair as alt
import pandas as pd
import streamlit as st


def build_sales_trend_chart(
    trend_df: pd.DataFrame,
    frequency: str,
) -> alt.Chart:
    """Build a chronological trend chart with explicit period labels."""
    label_format = "%b '%y" if frequency == "month" else "%b %d '%y"
    chart_df = trend_df.assign(period=trend_df["date"].dt.strftime(label_format))
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
                    "date:T",
                    title=tooltip_title,
                    format="%b %d, %Y",
                ),
                alt.Tooltip("amount:Q", title="Sales", format="$,.2f"),
            ],
        )
    )


def render_sales_trend(
    trend_df: pd.DataFrame,
    frequency: str,
) -> None:
    """Render sales periods with explicit labels for every time granularity."""
    chart = build_sales_trend_chart(trend_df, frequency)
    st.altair_chart(chart, width="stretch")

"""Linear-regression forecasts for cleaned sales data."""

import pandas as pd
from sklearn.linear_model import LinearRegression

from backend.transformation import sales_by_date


FORECAST_DAYS = 30
FORECAST_COLUMNS = ["date", "historical_sales", "forecast_sales"]
INSUFFICIENT_DATA_MESSAGE = (
    "Insufficient data for a sales forecast: at least two distinct dates "
    "with sales amounts are required."
)


def generate_sales_forecast(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Return observed daily sales and predictions for the next 30 days.

    The input is cleaned sales data with date and numeric amount columns.
    Only dates with recorded amounts are modeled; missing calendar days are
    not assumed to be zero. Invalid dates and missing amounts are excluded.
    Fewer than two distinct usable dates produce an empty result with the same
    columns. Linear extrapolation can produce negative sales predictions.
    """
    sales = sales_df.loc[:, ["date", "amount"]].copy()
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce").dt.normalize()
    sales = sales.dropna(subset=["date", "amount"])
    daily = sales_by_date(sales).reset_index(drop=True)
    if len(daily) < 2:
        return pd.DataFrame(columns=FORECAST_COLUMNS)

    first_date = daily["date"].iloc[0]
    last_date = daily["date"].iloc[-1]
    offsets = (daily["date"] - first_date).dt.days.to_numpy().reshape(-1, 1)
    model = LinearRegression().fit(offsets, daily["amount"].to_numpy())
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=FORECAST_DAYS)
    future_offsets = (future_dates - first_date).days.to_numpy().reshape(-1, 1)

    historical = daily.rename(columns={"amount": "historical_sales"})
    historical["forecast_sales"] = float("nan")
    future = pd.DataFrame({
        "date": future_dates,
        "historical_sales": float("nan"),
        "forecast_sales": model.predict(future_offsets),
    })
    return pd.concat([historical, future], ignore_index=True)[FORECAST_COLUMNS]


def generate_forecast_insight(forecast_df: pd.DataFrame) -> str:
    """Describe forecast direction, treating endpoint changes up to 5% as stable."""
    future = forecast_df["forecast_sales"].dropna()
    if future.empty:
        return INSUFFICIENT_DATA_MESSAGE

    first, last = float(future.iloc[0]), float(future.iloc[-1])
    change = last - first
    tolerance = 0.05 * max(abs(first), abs(last))
    if abs(change) <= tolerance:
        return "Projected daily sales remain relatively stable over the next 30 days."
    if change > 0:
        return "Daily sales are projected to increase over the next 30 days."
    return "Forecast indicates declining daily sales over the next 30 days."

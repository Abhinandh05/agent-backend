"""
Train a sales-forecast RandomForestRegressor on data/sales_data.csv.

Usage (from backend root, venv active):
    python -m ml.train_sales_forecast_model

Designed for Superstore-style CSVs (Order Date, Sales, Category, Region) but
auto-detects column names — prints headers first and adapts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "sales_data.csv"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODELS_DIR / "sales_forecast_model.pkl"
ACCURACY_CHART = MODELS_DIR / "sales_forecast_accuracy.png"

DATE_CANDIDATES = [
    "Order Date",
    "OrderDate",
    "order_date",
    "Date",
    "date",
    "InvoiceDate",
    "invoice_date",
    "Transaction Date",
]
SALES_CANDIDATES = [
    "Sales",
    "sales",
    "Sale",
    "Revenue",
    "revenue",
    "Amount",
    "amount",
    "Total",
    "total_sales",
    "Sales Amount",
]
# Low-cardinality categoricals only — Sub-Category / Product explode the
# feature space and fight a simple RF baseline. Category + Region (+ Segment)
# capture most retail structure without sparsity.
CAT_CANDIDATES = [
    "Category",
    "category",
    "Region",
    "region",
    "Segment",
    "segment",
]


def _require_dataset() -> Path:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_PATH}\n\n"
            "Recommended (simplest columns for a first regression model):\n"
            "  Kaggle Superstore Sales Dataset\n"
            "  https://www.kaggle.com/datasets/vivek468/superstore-dataset-final\n"
            "  (or Tableau Sample Superstore — Order Date, Sales, Category, Region)\n\n"
            "Alternative (harder time-series):\n"
            "  Kaggle Store Sales - Time Series Forecasting\n"
            "  https://www.kaggle.com/competitions/store-sales-time-series-forecasting\n\n"
            "Place / rename the CSV exactly to:\n"
            f"  {DATA_PATH}\n"
        )
    return DATA_PATH


def _pick_column(columns: list[str], candidates: list[str], kind: str) -> str:
    lower_map = {c.lower().strip(): c for c in columns}
    for cand in candidates:
        if cand in columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    raise ValueError(
        f"Could not auto-detect the {kind} column.\n"
        f"Columns found: {columns}\n"
        f"Expected one of: {candidates}"
    )


def _pick_optional_cats(columns: list[str]) -> list[str]:
    found: list[str] = []
    lower_map = {c.lower().strip(): c for c in columns}
    for cand in CAT_CANDIDATES:
        col = None
        if cand in columns:
            col = cand
        elif cand.lower() in lower_map:
            col = lower_map[cand.lower()]
        if col and col not in found:
            found.append(col)
    return found


def load_and_engineer(path: Path) -> tuple[pd.DataFrame, pd.Series, dict]:
    # Superstore exports sometimes use latin-1 / Windows encodings
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")

    # Strip BOM / whitespace from headers
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]

    print(f"Loaded {len(df)} rows × {len(df.columns)} columns from {path}")
    print(f"CSV columns: {list(df.columns)}")

    date_col = _pick_column(list(df.columns), DATE_CANDIDATES, "date")
    sales_col = _pick_column(list(df.columns), SALES_CANDIDATES, "sales/revenue")
    cat_cols = _pick_optional_cats(list(df.columns))
    print(f"Detected date column: {date_col}")
    print(f"Detected sales column: {sales_col}")
    print(f"Detected categorical column(s): {cat_cols}")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[sales_col] = pd.to_numeric(df[sales_col], errors="coerce")
    df = df.dropna(subset=[date_col, sales_col])

    # Calendar features — in retail sales, seasonality (month/quarter) and
    # day-of-week effects are usually stronger predictors than raw transaction
    # noise. These become the core numeric signal for RandomForest.
    df["year"] = df[date_col].dt.year
    df["month"] = df[date_col].dt.month
    df["day_of_week"] = df[date_col].dt.dayofweek  # Mon=0 … Sun=6
    df["quarter"] = df[date_col].dt.quarter

    # Aggregation choice: daily totals by category dimensions.
    # Raw Superstore rows are line-items (many per day). Training on individual
    # line amounts is noisy and not a useful "forecast" target. Summing to
    # daily sales (optionally split by Category/Region) yields a smoother
    # series that matches the business question: "how much will we sell on
    # this kind of day?". Daily is finer than monthly (more rows for RF) but
    # still removes per-SKU noise.
    df["_period"] = df[date_col].dt.normalize()
    group_keys = ["_period", "year", "month", "day_of_week", "quarter"] + cat_cols

    agg = (
        df.groupby(group_keys, as_index=False)[sales_col]
        .sum()
        .rename(columns={sales_col: "target_sales"})
    )
    print(
        f"Aggregated to {len(agg)} daily rows "
        f"(from {len(df)} transactions) using keys={group_keys}"
    )

    # Sort chronologically for the time-based split below
    agg = agg.sort_values("_period").reset_index(drop=True)

    y = agg["target_sales"]
    X = agg.drop(columns=["target_sales", "_period"])

    if cat_cols:
        X = pd.get_dummies(X, columns=cat_cols, drop_first=False)

    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    meta = {
        "date_col": date_col,
        "sales_col": sales_col,
        "cat_cols": cat_cols,
        "period_dates": agg["_period"],
    }
    return X, y, meta


def train() -> dict:
    _require_dataset()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X, y, meta = load_and_engineer(DATA_PATH)
    feature_columns = list(X.columns)
    n = len(X)
    split_idx = int(n * 0.8)

    # TIME-BASED split (not shuffled).
    # Common beginner mistake: train_test_split(..., shuffle=True) on a time
    # series. That leaks future rows into training, so test MAE looks
    # unrealistically good and the model fails in production. Always train on
    # earlier dates and test on later dates.
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    test_dates = meta["period_dates"].iloc[split_idx:]

    print(
        f"Time-based split: train={len(X_train)} (earlier), "
        f"test={len(X_test)} (later), random_state N/A for split"
    )

    # RandomForestRegressor: robust to mixed feature scales, no standardization
    # needed, fast on CPU. For production time-series you might reach for
    # Prophet, ARIMA, or XGBoost — RF is a solid, simple baseline here.
    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    # MAE / RMSE — regression metrics (not classification accuracy).
    # MAE = average absolute $ error; RMSE penalizes large misses more.
    print("\n=== Test-set evaluation (time-held-out) ===")
    print(f"MAE  (average error): ${mae:,.2f}")
    print(f"RMSE (root mean sq.): ${rmse:,.2f}")
    print(f"Test target mean:     ${float(y_test.mean()):,.2f}")
    print(f"Test target std:      ${float(y_test.std()):,.2f}")

    # Actual vs predicted over the test period (aggregate by calendar day for chart)
    chart_df = pd.DataFrame(
        {
            "date": pd.to_datetime(test_dates.values),
            "actual": y_test.values,
            "predicted": y_pred,
        }
    )
    daily = chart_df.groupby("date", as_index=False)[["actual", "predicted"]].sum()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(daily["date"], daily["actual"], label="Actual", color="#3b82f6", linewidth=1.5)
    ax.plot(
        daily["date"],
        daily["predicted"],
        label="Predicted",
        color="#10b981",
        linewidth=1.5,
        alpha=0.85,
    )
    ax.set_title("Sales Forecast — Actual vs Predicted (test period)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Sales ($)")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(ACCURACY_CHART, dpi=120)
    plt.close(fig)
    print(f"\nSaved accuracy chart → {ACCURACY_CHART}")

    artifact = {
        "model": model,
        "columns": feature_columns,
        "date_col": meta["date_col"],
        "sales_col": meta["sales_col"],
        "cat_cols": meta["cat_cols"],
        "metrics": {"mae": mae, "rmse": rmse},
    }
    joblib.dump(artifact, MODEL_PATH)

    print("\n=== Training complete ===")
    print(f"Model saved to: {MODEL_PATH}")
    print("Trained on CPU only — RandomForestRegressor baseline.")
    return artifact


def main() -> int:
    try:
        train()
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

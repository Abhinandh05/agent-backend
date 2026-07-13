"""
Train a Customer Segmentation K-Means model on Mall Customer data.

Usage (from the backend root, venv active):
    python -m ml.train_customer_segments

Requires: data/mall_customers.csv (download manually from Kaggle — see README).
Trains on CPU in a few seconds for ~200 rows.

Unlike churn / credit / sales models, this is UNSUPERVISED: there is no
Yes/No label. K-Means discovers natural customer groups from Age, Income,
and Spending Score alone.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import matplotlib

# Non-interactive backend so training works on headless / no-display machines
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "mall_customers.csv"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODELS_DIR / "segmentation_model.pkl"
ELBOW_PLOT = MODELS_DIR / "elbow_plot.png"
SCATTER_PLOT = MODELS_DIR / "segments_scatter.png"

# Canonical names we expose in the saved artifact / predict API
CANONICAL_FEATURES = ["Age", "Annual_Income", "Spending_Score"]


def _require_dataset() -> Path:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_PATH}\n\n"
            "Download the Mall Customer Segmentation Data CSV from Kaggle:\n"
            "  https://www.kaggle.com/datasets/vjchoudhary7/customer-segmentation-tutorial-in-python\n"
            "Search Kaggle for: \"Mall Customer Segmentation Data\"\n"
            "Then place/rename it exactly to:\n"
            f"  {DATA_PATH}\n"
        )
    return DATA_PATH


def _resolve_feature_columns(columns: list[str]) -> dict[str, str]:
    """
    Map canonical feature names → actual CSV column names.

    Kaggle re-uploads of this dataset often tweak spacing / punctuation, e.g.
    'Annual Income (k$)' vs 'Annual Income' vs 'AnnualIncome'.
    """
    lower_map = {c.lower().strip(): c for c in columns}

    def find_one(predicates: list, label: str) -> str:
        for key, original in lower_map.items():
            if any(p(key) for p in predicates):
                return original
        raise ValueError(
            f"Could not find a column for {label}. Actual columns: {columns}"
        )

    age = find_one([lambda k: k == "age"], "Age")
    income = find_one(
        [
            lambda k: "annual" in k and "income" in k,
            lambda k: k in ("annualincome", "income"),
        ],
        "Annual Income",
    )
    spending = find_one(
        [
            lambda k: "spending" in k and "score" in k,
            lambda k: k in ("spendingscore", "spending"),
        ],
        "Spending Score",
    )
    return {
        "Age": age,
        "Annual_Income": income,
        "Spending_Score": spending,
    }


def load_features(path: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows × {len(df.columns)} columns from {path}")
    print(f"Actual column names: {list(df.columns)}")

    col_map = _resolve_feature_columns(list(df.columns))
    print("Resolved feature columns:")
    for canonical, actual in col_map.items():
        print(f"  {canonical} ← '{actual}'")

    X = pd.DataFrame(
        {
            "Age": pd.to_numeric(df[col_map["Age"]], errors="coerce"),
            "Annual_Income": pd.to_numeric(
                df[col_map["Annual_Income"]], errors="coerce"
            ),
            "Spending_Score": pd.to_numeric(
                df[col_map["Spending_Score"]], errors="coerce"
            ),
        }
    )
    before = len(X)
    X = X.dropna().reset_index(drop=True)
    dropped = before - len(X)
    if dropped:
        print(f"Dropped {dropped} row(s) with non-numeric / missing features")
    return X, col_map


def choose_k_elbow(inertias: list[float], k_values: list[int]) -> int:
    """
    Pick k at the 'elbow' of the inertia curve.

    Elbow method (why it matters for unsupervised K-Means):
      - Inertia = within-cluster sum of squared distances to centroids.
      - As k grows, inertia always falls (more centroids fit tighter), so we
        cannot minimize inertia alone — that would pick k = n_samples.
      - The elbow is where adding another cluster stops buying much reduction
        in inertia (diminishing returns). That kink is a practical k.

    We locate the elbow as the point of maximum perpendicular distance from
    the line joining (k_min, inertia_min_k) to (k_max, inertia_max_k) — a
    simple geometric knee detector. For the classic Mall Customers dataset
    this usually lands near k=5; we still compute it from the curve rather
    than hardcoding blindly.
    """
    xs = np.array(k_values, dtype=float)
    ys = np.array(inertias, dtype=float)
    # Line from first to last point
    p1 = np.array([xs[0], ys[0]])
    p2 = np.array([xs[-1], ys[-1]])
    line = p2 - p1
    line_len = np.linalg.norm(line)
    if line_len == 0:
        return int(k_values[0])

    distances = []
    for x, y in zip(xs, ys):
        p = np.array([x, y])
        # Perpendicular distance from point to the line segment direction
        dist = np.abs(np.cross(line, p1 - p)) / line_len
        distances.append(float(dist))

    best_idx = int(np.argmax(distances))
    return int(k_values[best_idx])


def _label_clusters(profile: pd.DataFrame) -> dict[int, str]:
    """
    Assign human-readable business labels from each cluster's mean profile.

    Labels are derived from where each cluster sits relative to the median of
    cluster means for Income and Spending (and Age as a tie-breaker). We do
    NOT assume the textbook 5 mall segments always appear — we adapt to
    whatever centers K-Means actually found.
    """
    income_med = profile["Annual_Income"].median()
    spend_med = profile["Spending_Score"].median()
    age_med = profile["Age"].median()

    labels: dict[int, str] = {}
    used: set[str] = set()

    for cid, row in profile.iterrows():
        hi_inc = row["Annual_Income"] >= income_med
        hi_spend = row["Spending_Score"] >= spend_med
        older = row["Age"] >= age_med

        if hi_inc and hi_spend:
            name = "Premium Customers"
        elif (not hi_inc) and hi_spend:
            name = "Aspirational Spenders"
        elif hi_inc and (not hi_spend):
            name = "Cautious High-Earners"
        elif (not hi_inc) and (not hi_spend) and older:
            name = "Budget-Conscious"
        elif (not hi_inc) and (not hi_spend):
            name = "Value Seekers"
        else:
            name = "Standard Customers"

        # Disambiguate if two clusters map to the same label
        if name in used:
            age_tag = "Mature" if older else "Young"
            name = f"{name} ({age_tag})"
            if name in used:
                name = f"{name} [{cid}]"
        used.add(name)
        labels[int(cid)] = name

    return labels


def train() -> dict:
    _require_dataset()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X, col_map = load_features(DATA_PATH)
    feature_columns = list(X.columns)
    print(f"\nFeature matrix shape: {X.shape}")
    print(X.describe().round(2))

    # --- Feature scaling (REQUIRED for K-Means, unlike Random Forest) -------
    # K-Means assigns points by Euclidean distance to centroids. Age (~18–70),
    # Annual Income (k$ ~15–137), and Spending Score (1–100) live on different
    # numeric scales. Without StandardScaler, the largest-range feature would
    # dominate the distance calculation and distort the clusters. Random Forest
    # splits on one feature at a time, so it is scale-invariant — K-Means is not.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # --- Elbow method: try k = 2..10 ----------------------------------------
    k_values = list(range(2, 11))
    inertias: list[float] = []
    print("\n=== Elbow method (inertia vs k) ===")
    for k in k_values:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(float(km.inertia_))
        print(f"  k={k:2d}  inertia={km.inertia_:.2f}")

    chosen_k = choose_k_elbow(inertias, k_values)
    # Reasoning from the inertia curve on the Mall Customers CSV (Age +
    # Income + Spending): inertia falls sharply from k=2→4, then the
    # marginal gain slows (k=5+ still decreases but less steeply). The
    # geometric knee detector typically lands at k=4 here. Tutorials that
    # cluster on Income+Spending only often quote k=5 — with Age included
    # the bend can shift; always re-check elbow_plot.png for your CSV.
    print(
        f"\nChosen k={chosen_k} (elbow / knee of the inertia curve — "
        f"see {ELBOW_PLOT.name})"
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(k_values, inertias, marker="o", color="#2563eb", linewidth=2)
    ax.axvline(chosen_k, color="#dc2626", linestyle="--", label=f"chosen k={chosen_k}")
    ax.set_xlabel("Number of clusters (k)")
    ax.set_ylabel("Inertia (within-cluster sum of squares)")
    ax.set_title("Elbow Method — K-Means Customer Segmentation")
    ax.set_xticks(k_values)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(ELBOW_PLOT, dpi=120)
    plt.close(fig)
    print(f"Saved elbow plot → {ELBOW_PLOT}")

    # --- Final model --------------------------------------------------------
    model = KMeans(n_clusters=chosen_k, random_state=42, n_init=10)
    labels = model.fit_predict(X_scaled)
    X_profile = X.copy()
    X_profile["cluster"] = labels

    profile = (
        X_profile.groupby("cluster")[feature_columns]
        .mean()
        .round(2)
        .sort_index()
    )
    profile["count"] = X_profile.groupby("cluster").size()
    cluster_labels = _label_clusters(profile.drop(columns=["count"]))

    print("\n=== Cluster profiles (mean Age / Income / Spending) ===")
    print(f"{'cluster':>8}  {'label':<32}  {'Age':>6}  {'Income':>8}  {'Spend':>7}  {'n':>4}")
    for cid, row in profile.iterrows():
        print(
            f"{int(cid):>8}  {cluster_labels[int(cid)]:<32}  "
            f"{row['Age']:6.1f}  {row['Annual_Income']:8.1f}  "
            f"{row['Spending_Score']:7.1f}  {int(row['count']):4d}"
        )

    # Classic Income vs Spending Score scatter, colored by cluster
    fig, ax = plt.subplots(figsize=(8, 6))
    cmap = plt.get_cmap("tab10")
    for cid in sorted(cluster_labels.keys()):
        mask = labels == cid
        ax.scatter(
            X.loc[mask, "Annual_Income"],
            X.loc[mask, "Spending_Score"],
            c=[cmap(cid % 10)],
            label=f"{cid}: {cluster_labels[cid]}",
            alpha=0.75,
            edgecolors="white",
            linewidths=0.4,
            s=55,
        )
    # Plot centroids in original feature space (inverse-transform scaled centers)
    centers_orig = scaler.inverse_transform(model.cluster_centers_)
    # centers columns order matches feature_columns: Age, Annual_Income, Spending_Score
    ax.scatter(
        centers_orig[:, 1],
        centers_orig[:, 2],
        c="black",
        marker="X",
        s=160,
        label="centroids",
        zorder=5,
    )
    ax.set_xlabel("Annual Income")
    ax.set_ylabel("Spending Score")
    ax.set_title("Customer Segments — Income vs Spending Score")
    ax.legend(fontsize=8, loc="best")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(SCATTER_PLOT, dpi=120)
    plt.close(fig)
    print(f"Saved scatter plot → {SCATTER_PLOT}")

    artifact = {
        "model": model,
        "scaler": scaler,
        "cluster_labels": cluster_labels,
        "feature_columns": feature_columns,
        "source_column_map": col_map,
        "n_clusters": chosen_k,
        "cluster_profiles": {
            str(cid): {
                "label": cluster_labels[int(cid)],
                "mean_age": float(row["Age"]),
                "mean_annual_income": float(row["Annual_Income"]),
                "mean_spending_score": float(row["Spending_Score"]),
                "count": int(row["count"]),
            }
            for cid, row in profile.iterrows()
        },
    }
    joblib.dump(artifact, MODEL_PATH)

    print("\n=== Training complete ===")
    print(f"k={chosen_k}  |  model saved to: {MODEL_PATH}")
    print("Unsupervised K-Means on CPU — typically a few seconds on this dataset.")
    return artifact


def main() -> int:
    try:
        train()
    except (FileNotFoundError, ValueError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

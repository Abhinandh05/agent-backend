"""
Sanity-check sales forecast predictions with hardcoded examples.

Usage (after training):
    python -m scripts.test_sales_forecast
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.predict_sales_forecast import model_ready, predict_sales

# Examples match Superstore-style Category / Region + calendar fields.
# Historical daily slice totals are often tens–thousands of dollars; predictions
# should land in a similar ballpark (not millions, not zero).
EXAMPLES = [
    {
        "name": "Q4 Technology West — holiday season often strong",
        "features": {
            "year": 2017,
            "month": 11,
            "day_of_week": 1,
            "quarter": 4,
            "Category": "Technology",
            "Region": "West",
            "Segment": "Consumer",
        },
    },
    {
        "name": "Q1 Furniture South — quieter winter month",
        "features": {
            "year": 2017,
            "month": 2,
            "day_of_week": 3,
            "quarter": 1,
            "Category": "Furniture",
            "Region": "South",
            "Segment": "Corporate",
        },
    },
    {
        "name": "Mid-year Office Supplies East via date string",
        "features": {
            "Order Date": "2017-07-15",
            "Category": "Office Supplies",
            "Region": "East",
            "Segment": "Consumer",
        },
    },
]


def main() -> int:
    if not model_ready():
        print(
            "ERROR: Model file missing. Train first:\n"
            "  python -m ml.train_sales_forecast_model"
        )
        return 1

    print("=== Sales forecast prediction smoke test ===\n")
    for ex in EXAMPLES:
        result = predict_sales(ex["features"])
        print(f"→ {ex['name']}")
        print(json.dumps(result, indent=2))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

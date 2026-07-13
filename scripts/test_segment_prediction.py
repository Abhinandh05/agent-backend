"""
Sanity-check the customer-segmentation model with a few hardcoded customers.

Usage (from backend root, after training):
    python -m scripts.test_segment_prediction
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.predict_customer_segment import model_ready, predict_segment


EXAMPLES = [
    {
        "name": "Young high-spender (expect aspirational / premium-leaning)",
        "customer": {"age": 24, "annual_income": 25, "spending_score": 90},
    },
    {
        "name": "Older high-income low-spender (expect cautious high-earner)",
        "customer": {"age": 45, "annual_income": 90, "spending_score": 15},
    },
    {
        "name": "Average mid-range customer",
        "customer": {"age": 40, "annual_income": 55, "spending_score": 50},
    },
]


def main() -> int:
    if not model_ready():
        print(
            "ERROR: Model file missing. Train first:\n"
            "  python -m ml.train_customer_segments"
        )
        return 1

    print("=== Customer segment prediction smoke test ===\n")
    for ex in EXAMPLES:
        result = predict_segment(ex["customer"])
        print(f"→ {ex['name']}")
        print(f"  input: {ex['customer']}")
        print(json.dumps(result, indent=2))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

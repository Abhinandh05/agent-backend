"""
Sanity-check the spam classifier with a few hardcoded messages.

Usage (from backend root, after training):
    python -m scripts.test_spam_classifier
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.predict_spam import classify_message, model_ready


EXAMPLES = [
    {
        "name": "Obvious spam-style message",
        "text": "WIN FREE MONEY NOW!!! CLICK HERE http://bit.ly/prize to claim your $1000 cash prize urgently!!!",
    },
    {
        "name": "Normal business message",
        "text": (
            "Hi team, please review the Q3 budget draft attached and send "
            "comments by Friday. Thanks, Alex."
        ),
    },
    {
        "name": "Short ham-like SMS",
        "text": "Ok, I'll meet you at the office at 3pm.",
    },
]


def main() -> int:
    if not model_ready():
        print(
            "ERROR: Model file missing. Train first:\n"
            "  python -m ml.train_spam_classifier"
        )
        return 1

    print("=== Spam classifier smoke test ===\n")
    for ex in EXAMPLES:
        result = classify_message(ex["text"])
        print(f"→ {ex['name']}")
        print(f"  text: {ex['text'][:80]}{'...' if len(ex['text']) > 80 else ''}")
        print(json.dumps(result, indent=2))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

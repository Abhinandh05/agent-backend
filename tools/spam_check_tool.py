"""
CrewAI/LangChain tool wrapping the trained spam / ham text classifier.

# Design note (Email Agent):
# The Email Agent currently *drafts* outgoing messages. Spam screening is more
# natural for *incoming* content. Forcing this into the draft flow would be
# awkward ("classify the email I just wrote as spam?"). Instead we expose
# classify_message() primarily via POST /api/v1/ml/spam-check so the user can
# paste any message text for an instant screen. The tool below is still
# available if the agent is asked to evaluate pasted/incoming text.
"""
from __future__ import annotations

import json
from langchain.tools import Tool

from ml.predict_spam import classify_message


def _run_spam_check(text: str) -> str:
    """Accepts raw message text (or a JSON {"text": "..."} string)."""
    try:
        payload = text
        if isinstance(text, str) and text.strip().startswith("{"):
            data = json.loads(text)
            if isinstance(data, dict) and "text" in data:
                payload = data["text"]
        result = classify_message(str(payload))
        return json.dumps(result)
    except FileNotFoundError as exc:
        return f"Model not trained yet: {exc}"
    except Exception as exc:
        return f"Spam check failed: {exc}"


def get_spam_check_tool() -> Tool:
    return Tool(
        name="spam_message_classifier",
        description=(
            "Classify a pasted or incoming message as spam or ham (legitimate) "
            "using a trained TF-IDF + Naive Bayes text classifier. Input is the "
            "raw message text (or JSON {\"text\": \"...\"}). Returns is_spam, "
            "confidence, and label. Use when the user asks to screen/check "
            "whether a message looks like spam — not for drafting outgoing email."
        ),
        func=_run_spam_check,
    )

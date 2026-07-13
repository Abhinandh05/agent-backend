"""
Optional SendGrid email send.

If SENDGRID_API_KEY / SENDGRID_FROM_EMAIL are missing, callers get a clear
configuration error — drafting still works without them.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx


class EmailSendError(RuntimeError):
    """Raised when SendGrid is misconfigured or the API rejects the message."""


def send_email(
    to: str,
    subject: str,
    body: str,
    *,
    from_email: Optional[str] = None,
) -> dict:
    """
    Send a plain-text email via SendGrid v3.

    Returns {"status": "sent", "to": ..., "subject": ...} on success.
    """
    api_key = os.environ.get("SENDGRID_API_KEY", "").strip()
    sender = (from_email or os.environ.get("SENDGRID_FROM_EMAIL", "")).strip()

    if not api_key:
        raise EmailSendError(
            "SENDGRID_API_KEY is not set. Add it to .env to enable sending, "
            "or copy the draft and send it from your own mail client."
        )
    if not sender:
        raise EmailSendError(
            "SENDGRID_FROM_EMAIL is not set. Add a verified sender address to .env."
        )
    if not to or "@" not in to:
        raise EmailSendError("A valid recipient email address (to) is required.")
    if not subject.strip():
        raise EmailSendError("Subject cannot be empty.")
    if not body.strip():
        raise EmailSendError("Body cannot be empty.")

    payload = {
        "personalizations": [{"to": [{"email": to.strip()}]}],
        "from": {"email": sender},
        "subject": subject.strip(),
        "content": [{"type": "text/plain", "value": body}],
    }

    try:
        response = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        raise EmailSendError(f"Failed to reach SendGrid: {exc}") from exc

    if response.status_code not in (200, 201, 202):
        detail = response.text[:500] if response.text else response.reason_phrase
        raise EmailSendError(
            f"SendGrid rejected the message ({response.status_code}): {detail}"
        )

    return {"status": "sent", "to": to.strip(), "subject": subject.strip()}

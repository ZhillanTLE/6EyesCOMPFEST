"""
sender.py — Sends the approved notification by email.

Three rules this module exists to enforce.

1. SENDING NEVER HAPPENS DURING A PIPELINE RUN. It is reachable only from the
   approval endpoint. Clicking through six travelers to read their traces must
   not put six emails in anyone's inbox.

2. EVERY SEND GOES TO DEMO_RECIPIENT. The seeded travelers are synthetic and
   their addresses are invented; delivering to fabricated addresses bounces and
   damages the sending domain's reputation. The real traveler address is
   recorded in the response so the routing is visible rather than hidden.

3. FIXTURES DO NOT DISABLE SENDING. WINDFALL_FIXTURES replaces *inference*, not
   *delivery* -- the point of the flag is surviving a rate limit on judging day,
   and delivery still has to be demonstrable.

SEND_ENABLED=false renders the whole flow with delivery suppressed, for a
judging environment with no outbound SMTP. That is reported honestly as
"suppressed", never as "sent".

WhatsApp is preview-only and always will be for penyisihan: the Business API
requires verified business status and pre-approved message templates. The UI
labels that panel explicitly so the asymmetry reads as a decision rather than
a broken feature.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Optional

from .schemas import NotificationDraft


class SendState:
    SENT = "sent"
    SUPPRESSED = "suppressed"   # SEND_ENABLED=false; flow ran, nothing left
    FAILED = "failed"


@dataclass(frozen=True)
class SendReceipt:
    state: str
    channel: str = "email"
    recipient: Optional[str] = None
    subject: Optional[str] = None
    detail: Optional[str] = None


def _enabled() -> bool:
    return os.environ.get("SEND_ENABLED", "true").strip().lower() not in (
        "0", "false", "no")


def _recipient() -> Optional[str]:
    value = os.environ.get("DEMO_RECIPIENT", "").strip()
    return value or None


def send_email(draft: NotificationDraft, traveler_name: str,
               cart_id: str) -> SendReceipt:
    recipient = _recipient()

    if not _enabled():
        return SendReceipt(
            state=SendState.SUPPRESSED, recipient=recipient,
            subject=draft.subject,
            detail="SEND_ENABLED is false; the draft was not delivered.")

    if not recipient:
        return SendReceipt(
            state=SendState.FAILED, subject=draft.subject,
            detail=("DEMO_RECIPIENT is not set. Refusing to send: seeded "
                    "travelers have invented addresses and delivering to them "
                    "would bounce."))

    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        return SendReceipt(
            state=SendState.FAILED, recipient=recipient, subject=draft.subject,
            detail="SMTP_HOST is not set.")

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", user or "windfall@localhost").strip()

    message = EmailMessage()
    message["Subject"] = draft.subject
    message["From"] = sender
    message["To"] = recipient
    # The synthetic traveler this draft was written for. Recorded in a header
    # so a reader can see the routing rather than having to infer it.
    message["X-Windfall-Traveler"] = traveler_name
    message["X-Windfall-Cart"] = cart_id
    message.set_content(_plain_text(draft, traveler_name))

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(),
                                  timeout=20) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if user:
                    smtp.login(user, password)
                smtp.send_message(message)
    except Exception as exc:
        return SendReceipt(
            state=SendState.FAILED, recipient=recipient, subject=draft.subject,
            detail="SMTP error: {}".format(exc))

    return SendReceipt(state=SendState.SENT, recipient=recipient,
                       subject=draft.subject)


def _plain_text(draft: NotificationDraft, traveler_name: str) -> str:
    body = "\n\n".join(draft.body_paragraphs)
    return (
        "{}\n\n{}\n\n---\n"
        "Windfall demo. Ditulis untuk traveler: {}.\n"
        "Dikirim ke alamat demo, bukan ke traveler.\n"
    ).format(body, draft.cta_label, traveler_name)
